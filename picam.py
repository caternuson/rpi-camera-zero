import time
import os
import json
import asyncio
import tornado
from picamera2 import Picamera2

picam2 = Picamera2()
config = picam2.create_still_configuration( {"size":(1920, 1080)} )
picam2.configure(config)
picam2.start()

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
        resp = {"ERR":0}
        data = json.loads(self.request.body)
        #print(data)
        cmd = data.get("CMD", None)
        if cmd is None:
            resp["ERR"] = 1
            self.write(json.dumps(resp))
            return
        if cmd == "SPV":
            # start preview
            resp["URL"] = "http://blah.8081"
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
        elif cmd == "TAK":
            # take an image
            filename = "static/preview.jpg"
            url = "{}?{}".format(filename, time.time()) # prevent using cached image
            settings = picam2.capture_file(filename)
            resp["URL"] = url
            resp["SET"] = settings
        else:
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
