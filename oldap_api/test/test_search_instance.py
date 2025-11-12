
import string
import random

def test_instance_textsearch_A(client, token_headers, testemptydatamodeltest):
    header = token_headers[1]

    def random_string(length=12):
        chars = string.ascii_letters + string.digits
        return ''.join(random.choices(chars, k=length))

    for i in range(2):
        r = random_string()
        response = client.put('/data/test/Book', json={
            'title': f"Die Geschichte der {r}@de",
            'numPages': 6,
            'pubDate': "2026-01-01",
            'grantsPermission': 'oldap:GenericView'
        }, headers=header)
        assert response.status_code == 200
        book_iri = response.json['iri']
        for j in range(5):
            if j % 2 == 0:
                content = f"Waseliwas for page {j}\\n{random_string(100)}"
            else:
                content = f"Content for page {j}\\n{random_string(100)}"
            response = client.put('/data/test/Page', json={
                'test:pageDesignation': f"Page {j}",
                'test:pageNum': j,
                'test:pageDescription': f"Description for page {j}",
                'test:pageContent': content,
                'test:pageInBook': book_iri,
                'grantsPermission': 'oldap:GenericView'
            }, headers=header)

    response = client.get(f'/data/textsearch/test', query_string={
        "searchString": "waseliwas",
    }, headers=header)
    assert response.status_code == 200
    res = response.json
    print(res)

    assert len(res) == 4