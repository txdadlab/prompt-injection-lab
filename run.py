#!/usr/bin/env python3
"""Entry point for the Prompt Injection Lab."""

import uvicorn
import config

if __name__ == "__main__":
    uvicorn.run(
        "server.app:app",
        host=config.APP_HOST,
        port=config.APP_PORT,
        reload=False,
    )
