import random

def generate_otp() -> str:
    # Generates a random 6-digit number as a string
    return str(random.randint(100000, 999999))
