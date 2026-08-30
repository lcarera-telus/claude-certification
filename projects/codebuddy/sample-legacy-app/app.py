import handlers


def main():
    payload = {
        "name": "Spring Sale Quote",
        "country": "US",
        "discount": 12,
        "flagged": True,
        "items": [
            {"price": 19.99, "qty": 3},
            {"price": 5.5, "qty": 10},
        ],
    }
    result = handlers.handle_quote(payload)
    print(result)


if __name__ == "__main__":
    main()
