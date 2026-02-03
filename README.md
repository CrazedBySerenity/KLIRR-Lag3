# getting started

## Dependencies

```sh
pip3 install flask
```

## Run development server

```sh
flask --app server run
```

## Example requests

```sh
curl -X POST -H "Content-Type: application/json" \
-d '{"NAME": "John Doe", "DATE": "2024-04-27", "PRNR": "1234567890", "ADDRESS": "123 Main St", "POSTNR": "12345", "ZONKOD": "Z123"}' \
http://localhost:5000/generate
```

go to page `http://localhost:5000/pwa/<uid-return-from-generate>`
