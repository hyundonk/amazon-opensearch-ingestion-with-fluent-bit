from flask import Flask
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)

log_message = [{
    "level": "INFO",
    "message": "Good Morning!",
    "timestamp": "2024-07-18T12:00:00Z"
}]


@app.route('/')
def hello():
    app.logger.info(log_message)
    return 'Good morning!'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9090)
