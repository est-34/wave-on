def test_user_creation_points_to_readable_resource(client):
    created = client.post('/api/v1/users', json={'name': 'HTTP contract'})
    assert created.status_code == 201
    loaded = client.get(created.headers['location'])
    assert loaded.status_code == 200
    assert loaded.json()['id'] == created.json()['id']
    assert loaded.json()['name'] == 'HTTP contract'


def test_legacy_observation_remains_compatible(client):
    response = client.post('/api/v1/observe', json={
        'user_id': 'demo-user',
        'context': {'active_app': 'PowerPoint', 'activity': 'presentation'},
        'gesture': {'motion_type': 'swipe', 'direction': 'right', 'duration_ms': 430},
        'attempt_inference': False,
    })
    assert response.status_code == 200
    schema = client.get('/openapi.json').json()['paths']
    for old, new in [('/observe', '/observations'), ('/teach', '/teachings'),
                     ('/suggestions/{suggestion_id}/respond', '/suggestions/{suggestion_id}/responses')]:
        assert schema['/api/v1' + old]['post']['deprecated']
        assert '201' in schema['/api/v1' + new]['post']['responses']
