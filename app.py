from omaslib.src.connection import Connection

import factory

app = factory.factory()


@app.route('/')
def hello_world():  # put application's code here
    con = Connection(server='http://localhost:7200',
                         repo="omas",
                         userid="rosenth",
                         credentials="RioGrande",
                         context_name="DEFAULT")
    return con.token


if __name__ == '__main__':
    app.run()
