import os
import json
import asyncio
import tornado

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("picam.html")

class AjaxHandler(tornado.web.RequestHandler):
    def post(self):
        resp = {"ERR":0}
        data = json.loads(self.request.body)
        print(data)
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
        else:
            resp["ERR"] = 2
        self.write(json.dumps(resp))

async def main():
    handlers = [
        (r"/", MainHandler),
        (r"/ajax", AjaxHandler),
    ]
    settings = {
        "static_path": os.path.join(os.path.dirname(__file__), "static"),
        "template_path": os.path.join(os.path.dirname(__file__), "static"),
    }
    app = tornado.web.Application(handlers, **settings)
    app.listen(8888)
    shutdown_event = asyncio.Event()
    await shutdown_event.wait()

if __name__ == "__main__":
    asyncio.run(main())
