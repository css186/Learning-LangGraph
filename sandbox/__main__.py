from .config import settings
import uvicorn

def main():
    uvicorn.run(
        "sandbox.app:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        log_level=settings.LOG_LEVEL.lower(),
        reload=True,
    )


if __name__ == "__main__":
    main()