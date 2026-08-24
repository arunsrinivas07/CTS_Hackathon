import requests
import time
import json

base_url = 'http://localhost:8001/api/investigations'
payload = {
    'claim_id': '6',
    'claim_data': {},
    'risk_score': 0.95,
    'risk_level': 'HIGH'
}

print('Starting investigation...')
response = requests.post(f'{base_url}/start', json=payload)
if response.status_code != 200:
    print(f'Failed to start: {response.text}')
    exit(1)

inv_id = response.json()['investigation_id']
print(f'Started Investigation: {inv_id}')

for i in range(60):
    time.sleep(2)
    status_resp = requests.get(f'{base_url}/{inv_id}')
    data = status_resp.json()
    status = data.get('status')
    print(f'Step {i}: Status -> {status}')
    if status == 'COMPLETED' or status == 'FAILED':
        print(f'Final Output: {json.dumps(data, indent=2)}')
        break
