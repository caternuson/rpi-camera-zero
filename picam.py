import time
import os
import json
import asyncio
import tornado
from picamera2 import Picamera2
from PIL import Image, ImageDraw

picam2 = Picamera2()
config = picam2.create_still_configuration( {"size":(1920, 1080)} )
picam2.configure(config)
picam2.controls.AeEnable = False
picam2.controls.AwbEnable = False

# TODO: tweak these
picam2.controls.Brightness = 0.0  # -1.0 to 1.0 (0.0)
picam2.controls.Contrast = 1.0 # 0.0 to 32.0 (1.0)
picam2.controls.Saturation = 1.0 # 0.0 to 32.0 (1.0)
picam2.controls.Sharpness = 1.0 # 0.0 to 16.0 (1.0)
picam2.controls.ExposureTime = 1000000

#====================================================================
#                  S U P P O R T    F U N C T I O N S
#====================================================================
def capture_with_histogram(filename):
        """Capture an image with histogram overlay and save to specified file.
        Returns dictionary of camera settings used for original image.
        """
        # capture then open in PIL image
        hname = 'hist_' + time.strftime("%H%M%S", time.localtime()) + '.jpg'
        picam2.start()
        settings = picam2.capture_file(hname)
        picam2.stop()
        im_in   = Image.open(hname)
        im_out  = Image.new('RGB', im_in.size)
        im_out.paste(im_in)
        width, height = im_out.size
        draw = ImageDraw.Draw(im_out)

        # add rule of thirds lines
        x1 = width/3
        x2 = 2*x1
        y1 = height/3
        y2 = 2*y1
        draw.line([(x1,0),(x1,height)], width=3)
        draw.line([(x2,0),(x2,height)], width=3)
        draw.line([(0,y1),(width,y1)], width=3)
        draw.line([(0,y2),(width,y2)], width=3)

        # compute histogram, scaled for image size
        hist = im_in.histogram()
        rh = hist[0:256]
        gh = hist[256:512]
        bh = hist[512:768]
        xs = float(width)/float(256)
        ys = float(height)/float(max(hist))
        rl=[]
        gl=[]
        bl=[]
        for i in range(256):
            rl.append((int(i*xs),height-int(rh[i]*ys)))
            gl.append((int(i*xs),height-int(gh[i]*ys)))
            bl.append((int(i*xs),height-int(bh[i]*ys)))
        # draw it
        lw = int((0.01*max(im_out.size)))
        draw.line(rl, fill='red', width=lw, joint='curve')
        draw.line(gl, fill='green', width=lw, joint='curve')
        draw.line(bl, fill='blue', width=lw, joint='curve')

        # save it and clean up
        im_out.save(filename, quality=95)
        os.remove(hname)

        return settings


#====================================================================
#                        W E B    S E R V E R
#====================================================================

class MainHandler(tornado.web.RequestHandler):

    def get(self):
        time_lapse_running = self.application.settings.get("time_lapse_running", False)
        if time_lapse_running:
            self.render("status.html")
            #print("status")
        else:
            self.render("config.html")
            #self.application.settings["time_lapse_running"] = False
            #print("config")

    def post(self):
        resp = {"ERR":0} # 0=success
        data = json.loads(self.request.body)
        print(data)
        cmd = data.get("CMD", None)
        if cmd is None:
            # invalid request
            resp["ERR"] = 1
            self.write(json.dumps(resp))
            return
        if cmd == "SPV":
            # start preview
            pass
        elif cmd == "XPV":
            #stop preview
            pass
        elif cmd == "STA":
            # start time lapse
            self.application.settings["time_lapse_running"] = True
        elif cmd == "STO":
            # stop time lapse
            self.application.settings["time_lapse_running"] = False
        elif cmd == "TIM":
            # return system time
            resp["TIME"] = time.time()
        elif cmd == "HST":
            # take a histogram overlay image
            filename = "static/preview.jpg"
            settings = capture_with_histogram(filename)
            url = "{}?{}".format(filename, time.time()) # prevent using cached image
            resp["URL"] = url
            resp["SET"] = json.dumps(settings)
        elif cmd == "CAM":
            # configure camera
            cam_shutter = int(data.get("cam_shutter", "20000"))
            cam_gain = float(data.get("cam_gain", "0"))
            print("shutter:{}  gain:{}".format(cam_shutter, cam_gain))
            picam2.controls.ExposureTime = cam_shutter
            picam2.controls.AnalogueGain = cam_gain
        else:
            # unknown command
            resp["ERR"] = 2
        self.write(json.dumps(resp))

async def main():
    handlers = [
        (r"/", MainHandler),
    ]
    settings = {
        "static_path": os.path.join(os.path.dirname(__file__), "static"),
        "template_path": os.path.join(os.path.dirname(__file__), "static"),
        "time_lapse_running": False,
    }
    app = tornado.web.Application(handlers, **settings)
    app.listen(8888)
    print("Server started.")
    shutdown_event = asyncio.Event()
    await shutdown_event.wait()

if __name__ == "__main__":
    asyncio.run(main())
