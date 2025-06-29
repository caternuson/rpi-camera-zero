import time
import os
import json
import asyncio
import threading
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

class TimeLapser(threading.Thread):
    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None):
        threading.Thread.__init__(self, group=group, target=target, name=name)

        self.keep_running = True
        self.waiter = threading.Event()

        self.camera = kwargs.get('camera', None)
        self.delta_time = kwargs.get('delta_time', None)
        self.total_imgs = kwargs.get('total_imgs', None)

        self._status = {
            "name" : time.strftime("%Y%m%d_%H%M",time.localtime()),
            "delta_time" : self.delta_time,
            "total_imgs" : self.total_imgs,
            "image_count" : 0,
            "remaining_imgs" : self.total_imgs,
            "wait_time" : self.delta_time,
            "running" : False,
        }

    def run(self):
        self._status["running"] = True

        # make a new directory for images
        DIR = os.path.join(os.getcwd(), self._status["name"])
        os.mkdir(DIR)

        # dump info to file
        infofile = self._status["name"] + "_info.txt"
        with open(os.path.join(DIR, infofile), "w") as file:
            file.write("NAME:{}\n".format(self._status["name"]))
            file.write("TOTAL IMGS = {}\n".format(self._status["total_imgs"]))
            file.write("DELTA TIME = {}\n".format(self._status["delta_time"]))
            file.write("-"*15+"\n")
            file.write("CAMERA CONFIG\n")
            file.write("-"*15+"\n")
            for k, v in self.camera.camera_config.items():
                file.write("{}:{}\n".format(k, v))

        # timelapse loop
        count = 0
        while self.keep_running:
            count += 1
            self._status["image_count"] = count

            filename = self._status["name"]+"_{:04d}.jpg".format(count)
            filename = os.path.join(DIR, filename)

            # -- TAKE IMAGE --
            print("TAKE", count)
            acquire_start = time.time()
            self.camera.start()
            self.camera.capture_file(filename)
            self.camera.stop()
            # -- TAKE IMAGE --

            remaining_imgs = self._status["total_imgs"] - count
            self._status["remaining_imgs"] = remaining_imgs
            if remaining_imgs < 1:
                self.stop()
                return

            acquire_next = acquire_start + self._status["delta_time"]
            wait_time = acquire_next - time.time()
            self._status["wait_time"] = wait_time
            print("WAIT...")
            while self.keep_running and wait_time > 0:
                wait_time = acquire_next - time.time()
                self._status["wait_time"] = wait_time
                self.waiter.wait(0.25)

    def stop(self):
        self.keep_running = False
        self._status["running"] = False
        self.waiter.set()

    def status(self):
        return self._status

#====================================================================
#                        W E B    S E R V E R
#====================================================================

class MainHandler(tornado.web.RequestHandler):

    timelapser = None
    delta_time = None
    total_imgs = None

    def get(self):
        time_lapse_running = False
        if MainHandler.timelapser is not None:
            if MainHandler.timelapser.is_alive():
                time_lapse_running = True
        if time_lapse_running:
            self.render("status.html")
        else:
            self.render("config.html")

    def post(self):
        data = json.loads(self.request.body)
        #print(data)
        cmd = data.get("CMD", None)
        resp = {"ERR":0} # 0=success

        if cmd is None:
            #-------------------
            # invalid request
            #-------------------
            resp["ERR"] = 1
            # self.write(json.dumps(resp))
            # return
        elif cmd == "SPV":
            #-------------------
            # start preview
            #-------------------
            pass
        elif cmd == "XPV":
            #-------------------
            #stop preview
            #-------------------
            pass
        elif cmd == "STA":
            #-------------------
            # start time lapse
            #-------------------
            cfg = data.get("CFG")
            delta_time = float(cfg.get("delta_time", "0"))
            total_imgs = int(cfg.get("total_imgs", "0"))
            print(delta_time, total_imgs)
            self.__start_timelapse(delta_time, total_imgs)
            resp["STA"] = True
            #self.render("status.html")
            #return
        elif cmd == "STO":
            #-------------------
            # stop time lapse
            #-------------------
            self.__stop_timelapse()
            resp["STO"] = True
        elif cmd == "TIM":
            #-------------------
            # return system time
            #-------------------
            resp["TIME"] = time.time()
        elif cmd == "HST":
            #-------------------
            # take a histogram overlay image
            #-------------------
            filename = "static/preview.jpg"
            settings = capture_with_histogram(filename)
            url = "{}?{}".format(filename, time.time()) # prevent using cached image
            resp["URL"] = url
            resp["SET"] = json.dumps(settings)
        elif cmd == "CAM":
            #-------------------
            # configure camera
            #-------------------
            cam_shutter = int(data.get("cam_shutter", "20000"))
            cam_gain = float(data.get("cam_gain", "0"))
            print("shutter:{}  gain:{}".format(cam_shutter, cam_gain))
            picam2.controls.ExposureTime = cam_shutter
            picam2.controls.AnalogueGain = cam_gain
        elif cmd == "TLS":
            #-------------------
            # timelapse status
            #-------------------
            if MainHandler.timelapser is not None:
                status = MainHandler.timelapser.status()
                print(status)
                resp["TLS"] = json.dumps(status)
        else:
            #-------------------
            # unknown command
            #-------------------
            resp["ERR"] = 2

        self.write(json.dumps(resp))

    def __start_timelapse(self, delta_time, total_imgs):
        # does it exist?
        if MainHandler.timelapser is not None:
            # it exists, is it done?
            if not MainHandler.timelapser.is_alive():
                # throw it away
                MainHandler.timelapser = None
        # does it not exist?
        if MainHandler.timelapser is None:
            # create it
            MainHandler.timelapser = TimeLapser(kwargs={
                'camera': picam2,
                'delta_time' : delta_time,
                'total_imgs' : total_imgs,
            })
            # start it
            MainHandler.timelapser.start()

    def __stop_timelapse(self):
        if MainHandler.timelapser is not None:
            MainHandler.timelapser.stop()
            MainHandler.timelapser = None


async def main():
    handlers = [
        (r"/", MainHandler),
    ]
    settings = {
        "static_path": os.path.join(os.path.dirname(__file__), "static"),
        "template_path": os.path.join(os.path.dirname(__file__), "static"),
    }
    app = tornado.web.Application(handlers, **settings)
    app.listen(8888)
    print("Server started.")
    shutdown_event = asyncio.Event()
    await shutdown_event.wait()

if __name__ == "__main__":
    asyncio.run(main())
