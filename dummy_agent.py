import time
import sys

def main():
    print("Agent started. Preparing to perform action...")
    time.sleep(1)
    print("Action: Delete all files in /tmp/sensitive_data")
    time.sleep(1)
    print("Do you want to proceed? [y/n]")
    sys.stdout.flush()
    
    response = sys.stdin.readline().strip()
    if response.lower() == 'y':
        print("Action confirmed. Deleting files...")
        time.sleep(1)
        print("Done.")
    else:
        print("Action cancelled.")

if __name__ == "__main__":
    main()
