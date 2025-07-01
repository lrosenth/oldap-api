import io


def test_upload_hlist(client, token_headers):
    header = token_headers[1]

    data = {
        'yamlfile': (io.BytesIO(
            """
---
Gender:
    label:
      - Gender@en
      - Geschlecht@de
      - Genre@fr
    nodes:
      female:
        label: [ Female@en, Weiblich@de, Femelle@fr ]
      male:
        label: [ Male@en, Männlich@de, Mâle@fr ]
""".encode('utf-8')
        ), 'example.yaml')
    }

    response = client.post(
        '/admin/hlist/hyha/upload',
        headers=header,
        content_type='multipart/form-data',
        data=data
    )
    assert response.status_code == 200
    print(response.json)

    response = client.get('/admin/hlist/hyha/Gender', headers=header)
    assert response.status_code == 200
    print(response.json)

def test_upload_hlist_invalid(client, token_headers):
    header = token_headers[1]

    data = {
        'yamlfile': (io.BytesIO(
            """
{gaga: Dies ist ein test}
""".encode('utf-8')
        ), 'example.yaml')
    }

    response = client.post(
        '/admin/hlist/hyha/upload',
        headers=header,
        content_type='multipart/form-data',
        data=data
    )
    assert response.status_code == 400
    print(response.json)

def test_upload_hlist_no_priv(client, token_headers, testproject):
    header = token_headers[1]

    client.put('/admin/user/rosmangaga', json={
        "givenName": "Gagauser",
        "familyName": "Gagtest",
        "email": "gaga@gaga.com",
        "password": "gaga1234",
        "inProjects": [
            {
                "project": "http://www.salsah.org/version/2.0/SwissBritNet",
            }
        ],
        "hasPermissions": [
            "GenericRestricted"
        ]
    }, headers=header)

    login = client.post('/admin/auth/rosmangaga', json={'password': 'gaga1234'})
    token = login.json['token']
    header = {
        'Authorization': f'Bearer {token}'
    }

    data = {
        'yamlfile': (io.BytesIO(
            """
---
Gender:
    label:
      - Gender@en
      - Geschlecht@de
      - Genre@fr
    nodes:
      female:
        label: [ Female@en, Weiblich@de, Femelle@fr ]
      male:
        label: [ Male@en, Männlich@de, Mâle@fr ]
""".encode('utf-8')
        ), 'example.yaml')
    }

    response = client.post(
        '/admin/hlist/hyha/upload',
        headers=header,
        content_type='multipart/form-data',
        data=data
    )
    assert response.status_code == 403
    print(response.json)


