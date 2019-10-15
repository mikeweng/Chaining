import os
from chain import app

if __name__ == '__main__':
    env = os.environ
    app.run(
        host=env.get('FC_SVC_HOST', '127.0.0.1'),
        port=env.get('FC_SVC_PORT', 8080),
        debug=True
    )
