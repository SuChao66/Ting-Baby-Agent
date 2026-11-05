#!/usr/bin/env python3
# -*- coding:utf-8 -*-

from fastapi import FastAPI

app = FastAPI(title="Ting Baby Agent", description="Ting Baby Agent API", version="0.1.0")

@app.get("/")
def root():
    return {"message": "Hello, World!"}

@app.get("/items/{item_id}")
def get_item(item_id: str)-> dict[str, str]:
    return {"item_id": item_id}


