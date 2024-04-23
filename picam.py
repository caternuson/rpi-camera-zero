import os
import asyncio
import tornado

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("picam.html")

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
    shutdown_event = asyncio.Event()
    await shutdown_event.wait()

if __name__ == "__main__":
    asyncio.run(main())
