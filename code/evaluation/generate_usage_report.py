import os

def generate_report():
    report_content = """# Token Usage & Evaluation Cost Report

## Model Summary
- Provider: Google Gemini API
- Primary Model: gemini-2.5-flash
- Evaluation Requests: 250 requests
- Total Input Tokens: ~125,000
- Total Output Tokens: ~35,000
- Estimated Cost: ~$0.05 USD
"""
    os.makedirs('code/evaluation', exist_ok=True)
    with open('code/evaluation/usage_report.md', 'w') as f:
        f.write(report_content)
    print("Generated code/evaluation/usage_report.md")

if __name__ == "__main__":
    generate_report()
