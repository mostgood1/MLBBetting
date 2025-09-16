from app import app
from datetime import datetime


def main():
    client = app.test_client()
    def get(path):
        resp = client.get(path)
        try:
            return resp.status_code, resp.get_json()
        except Exception:
            return resp.status_code, {'text': resp.get_data(as_text=True)}

    print("-- /api/diag BEFORE warm --")
    code, data = get('/api/diag')
    print(code, data)

    today = datetime.now().strftime('%Y-%m-%d')
    print("-- /api/warm sync quick_only=1 --")
    code, data = get(f'/api/warm?date={today}&quick_only=1')
    print(code, data)

    print("-- /api/diag AFTER warm --")
    code, data = get('/api/diag')
    print(code, data)


if __name__ == '__main__':
    main()
