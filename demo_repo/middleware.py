import traceback


class App:
    def add_middleware(self, middleware, allow_origins):
        return (middleware, allow_origins)

    def exception_handler(self, _error_type):
        def decorator(fn):
            return fn

        return decorator


class CORSMiddleware:
    pass


app = App()

app.add_middleware(CORSMiddleware, allow_origins=["*"])


@app.exception_handler(Exception)
def handle_error(request, exc):
    return {"error": str(exc), "trace": traceback.format_exc()}

