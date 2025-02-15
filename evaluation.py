import os
import json
import pandas as pd
from typing import Dict, List, Set
import asyncio
from openai import AsyncOpenAI
from datetime import datetime

class CoverageAnalyzer:
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)
        print("Initializing CoverageAnalyzer...")
        self.cases_data = self.load_cases_data()
        print(f"Loaded cases data: {list(self.cases_data.keys())}")
    
    def load_cases_data(self) -> Dict[str, List[str]]:
        """Load cases and their key questions from CSV"""
        try:
            print("Loading cases data from CSV...")
            df = pd.read_csv('privacy_cases.csv')
            print(f"CSV columns: {df.columns.tolist()}")
            cases_data = {}
            for _, row in df.iterrows():
                case_name = row['Case']
                print(f"\nProcessing case: {case_name}")
                # Split key questions into a list and clean them
                if pd.isna(row['Key Questions']):
                    print(f"Warning: No key questions found for {case_name}")
                    continue
                key_questions = [q.strip() for q in row['Key Questions'].split('\n') if q.strip()]
                print(f"Found {len(key_questions)} key questions")
                cases_data[case_name] = key_questions
            return cases_data
        except Exception as e:
            print(f"Error loading cases data: {e}")
            import traceback
            print(traceback.format_exc())
            return {}

    def load_json_file(self, filepath: str) -> List[Dict]:
        try:
            print(f"\nLoading JSON file: {filepath}")
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"Successfully loaded JSON with {len(data)} items")
                return data
        except Exception as e:
            print(f"Error loading {filepath}: {e}")
            import traceback
            print(traceback.format_exc())
            return []

    def extract_questions(self, data: List[Dict], method: str) -> List[str]:
        print(f"\nExtracting questions for method: {method}")
        questions = []
        try:
            if method == "AGENT":
                for qa in data:
                    if isinstance(qa, dict) and 'question' in qa:
                        if isinstance(qa['question'], dict):
                            questions.append(qa['question'].get('text', ''))
                        else:
                            questions.append(str(qa['question']))
            else:  # BASE or PRE_DEFINE
                for item in data:
                    if isinstance(item, dict):
                        if 'question' in item:
                            if isinstance(item['question'], str):
                                questions.append(item['question'])
                            elif isinstance(item['question'], dict):
                                questions.append(item['question'].get('text', ''))
            
            print(f"Extracted {len(questions)} questions")
            if questions:
                print("Sample question:", questions[0])
            return questions
        except Exception as e:
            print(f"Error extracting questions: {e}")
            import traceback
            print(traceback.format_exc())
            return []

    async def analyze_coverage(
        self, 
        case_name: str,
        key_questions: List[str], 
        method_questions: List[str]
    ) -> Dict:
        print(f"\nAnalyzing coverage for {case_name}")
        print(f"Key questions count: {len(key_questions)}")
        print(f"Method questions count: {len(method_questions)}")
        
        prompt = f"""Analyze how well the generated questions cover the key questions for the {case_name} case.

Key Questions:
{json.dumps(key_questions, indent=2)}

Generated Questions:
{json.dumps(method_questions, indent=2)}

For each key question:
1. Determine if it is covered by any generated questions
2. Identify which specific generated questions cover it
3. Explain how the generated questions address the key question
4. Consider both direct matches and questions that address the same underlying privacy concern

Return analysis in JSON format:
{{
    "coverage_analysis": [
        {{
            "key_question": "The original key question",
            "is_covered": true/false,
            "covered_by": [
                {{
                    "question": "The generated question that covers it",
                    "explanation": "Detailed explanation of how this question addresses the key question's privacy concerns"
                }}
            ]
        }}
    ],
    "summary": {{
        "total_key_questions": number,
        "covered_questions": number,
        "coverage_percentage": number,
        "overall_assessment": "Detailed assessment of coverage quality, noting any gaps or areas of strong coverage"
    }}
}}"""

        try:
            print("Sending request to GPT-4...")
            response = await self.client.chat.completions.create(
                model="gpt-4",
                messages=[{
                    "role": "system",
                    "content": prompt
                }],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            print("Successfully received and parsed GPT-4 response")
            return result
            
        except Exception as e:
            print(f"Error in GPT analysis: {e}")
            import traceback
            print(traceback.format_exc())
            return None

    async def analyze_directory(self, directory: str) -> Dict:
        """Analyze all relevant files in the directory using case-specific key questions"""
        print(f"\nAnalyzing directory: {directory}")
        results = {}
        methods = ['BASE', 'PRE_DEFINE', 'AGENT']
        
        # List all files in directory
        files = os.listdir(directory)
        print(f"Found {len(files)} files in directory")
        print("Files:", files)
        
        for filename in files:
            matched_method = None
            for method in methods:
                if f'_{method}' in filename and filename.endswith('.json'):
                    matched_method = method
                    break
                    
            if matched_method:
                case_name = filename.split('_')[0]  # Extract case name
                print(f"\nProcessing file: {filename}")
                print(f"Extracted case name: {case_name}")
                
                # Skip if we don't have key questions for this case
                if case_name not in self.cases_data:
                    print(f"Skipping {filename} - no key questions found for {case_name}")
                    continue
                
                filepath = os.path.join(directory, filename)
                key_questions = self.cases_data[case_name]
                
                # Load and analyze file
                print(f"Analyzing {case_name} - {matched_method}...")
                data = self.load_json_file(filepath)
                if not data:
                    print(f"No data found in {filename}, skipping...")
                    continue
                    
                questions = self.extract_questions(data, matched_method)
                if not questions:
                    print(f"No questions extracted from {filename}, skipping...")
                    continue
                
                # Analyze coverage using GPT
                coverage_analysis = await self.analyze_coverage(
                    case_name,
                    key_questions, 
                    questions
                )
                
                if coverage_analysis:
                    # Store results
                    if case_name not in results:
                        results[case_name] = {}
                    results[case_name][matched_method] = {
                        'coverage_analysis': coverage_analysis,
                        'question_count': len(questions),
                        'questions': questions
                    }
                    
                    # Save interim results
                    self.save_results(results, f'coverage_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
                    print(f"Saved interim results for {case_name} - {matched_method}")
                else:
                    print(f"No coverage analysis results for {filename}")
                
                # Add delay to respect API rate limits
                await asyncio.sleep(1)
        
        return results

    def save_results(self, results: Dict, filename: str):
        """Save analysis results to file"""
        try:
            print(f"\nSaving results to {filename}")
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print("Results saved successfully")
        except Exception as e:
            print(f"Error saving results: {e}")
            import traceback
            print(traceback.format_exc())

async def main():
    print("Starting analysis...")
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("ERROR: No API key found")
        raise ValueError("Please set OPENAI_API_KEY environment variable")

    print("API key loaded successfully")
    analyzer = CoverageAnalyzer(api_key)
    
    if not analyzer.cases_data:
        print("ERROR: No cases data loaded")
        return
        
    results = await analyzer.analyze_directory('results')
    
    if not results:
        print("ERROR: No results generated")
        return
    
    # Print summary
    print("\nAnalysis Results:")
    print("-" * 50)
    for case, methods in results.items():
        print(f"\nCase: {case}")
        for method, data in methods.items():
            coverage = data['coverage_analysis']['summary']
            print(f"{method}:")
            print(f"  Coverage: {coverage['coverage_percentage']}%")
            print(f"  Covered Questions: {coverage['covered_questions']}/{coverage['total_key_questions']}")
            print(f"  Assessment: {coverage['overall_assessment']}")

if __name__ == "__main__":
    asyncio.run(main())