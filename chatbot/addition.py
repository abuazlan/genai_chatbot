def main():
    try:
        # Accept two numbers from the user
        num1 = float(input("Enter the first number: "))
        num2 = float(input("Enter the second number: "))

        # Perform an operation (e.g., addition)
        result = num1 + num2

        # Print the result
        print(f"The sum of {num1} and {num2} is {result}.")
    except ValueError:
        print("Invalid input. Please enter valid numbers.")

if __name__ == "__main__":
    main()
