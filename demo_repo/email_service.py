class Requests:
    def post(self, url, json):
        return {"url": url, "json": json}


requests = Requests()


def send_analytics(user):
    requests.post(
        "https://analytics.example.com",
        json={
            "email": user.email,
            "dob": user.date_of_birth,
            "ssn": user.ssn,
        },
    )

