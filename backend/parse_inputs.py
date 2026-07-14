from html.parser import HTMLParser

class InputParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.inputs = []

    def handle_starttag(self, tag, attrs):
        if tag == "input":
            self.inputs.append(dict(attrs))

def main():
    filepath = "/Users/apple/Desktop/All Project/All_Automation/AutoWebAgent/backend/logs/linkedin_login.html"
    with open(filepath, "r") as f:
        html = f.read()
        
    parser = InputParser()
    parser.feed(html)
    
    print(f"Total inputs found in HTML: {len(parser.inputs)}")
    for idx, attrs in enumerate(parser.inputs):
        print(f"[{idx+1}] attributes={attrs}")

if __name__ == "__main__":
    main()
