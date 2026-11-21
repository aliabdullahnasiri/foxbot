from fastapi import FastAPI


class App:
    def create(self) -> FastAPI:
        app = FastAPI(title="FoxBot", version="0.1.0")
        self.register_routers(app)
        return app

    @staticmethod
    def register_routers(app: FastAPI) -> None:
        from bot.api.routes import create_app_router

        app.include_router(create_app_router())


def main() -> FastAPI:
    return App().create()
