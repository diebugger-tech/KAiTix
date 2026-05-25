try:
    from app.main import app
    print("FASTAPI LOADED SUCCESSFULLY")
except Exception as e:
    import traceback
    traceback.print_exc()
