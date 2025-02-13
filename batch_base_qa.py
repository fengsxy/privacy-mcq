import os
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import json
import asyncio
import csv
from openai import AsyncOpenAI, OpenAI
import pandas as pd

@dataclass
class Question:
    text: str
    options: List[Dict[str, str]]
    category: str

@dataclass
class Answer:
    selected_options: List[str] 
    explanation: str

@dataclass
class QAPair:
    question: Question
    answer: Answer
    timestamp: str

@dataclass
class CaseData:
    case_name: str
    design_purpose: str
    data_practice: str
    key_questions: str

class QuestionAgent:
    def __init__(self, client: AsyncOpenAI):
        self.client = client

    async def generate_question(self, design_purpose: str, qa_history: List[QAPair]) -> Question:
        history_str = "\n".join([
            f"Q{i+1}: {qa.question.text}\nA{i+1}: {qa.answer.explanation}"
            for i, qa in enumerate(qa_history)
        ])
        
        system_prompt = f"""You are a Privacy Askinator that helps people design data practices.

Design Purpose: {design_purpose}

Previous QA History:
{history_str}

Current stage: {len(qa_history) + 1}

Based on the design purpose and previous answers, generate the next appropriate privacy question.
Follow these rules:
3. Each question must include 3-5 multiple choice options
4. Must return JSON format:
{{
    "text": "Question text here",
    "options": [
        {{"id": "option1", "label": "Option 1 description"}},
        {{"id": "option2", "label": "Option 2 description"}}
    ],
    "category": "category_name"
}}"""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",  # Using gpt-4 instead of gpt-4o
                messages=[{
                    "role": "system",
                    "content": system_prompt
                }],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return Question(
                text=result["text"],
                options=result["options"],
                category=result["category"]
            )
            
        except Exception as e:
            print(f"Error generating question: {e}")
            raise

class AnswerAgent:
    def __init__(self, client: AsyncOpenAI):
        self.client = client

    async def generate_answer(self, data_practice: str, question: Question) -> Answer:
        system_prompt = f"""You are a Privacy Answer Agent that helps analyze data practices.

Data Practice:
{data_practice}

Current Question: {question.text}
Options:
{json.dumps(question.options, indent=2)}

Analyze the data practice and select the most appropriate answer options.
Consider privacy implications, user expectations, and ethical considerations.

Must return JSON format:
{{
    "selected_options": ["option1", "option2"],
    "explanation": "Detailed explanation of why these options were selected"
}}"""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",  # Using gpt-4 instead of gpt-4o
                messages=[{
                    "role": "system",
                    "content": system_prompt
                }],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return Answer(
                selected_options=result["selected_options"],
                explanation=result["explanation"]
            )
            
        except Exception as e:
            print(f"Error generating answer: {e}")
            raise

class PrivacyAnalyzer:
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)
        self.question_agent = QuestionAgent(self.client)
        self.answer_agent = AnswerAgent(self.client)

    async def analyze_case(self, case: CaseData, max_pairs: int = 5) -> List[QAPair]:
        """Analyze a single case"""
        qa_history: List[QAPair] = []
        try:
            while len(qa_history) < max_pairs:
                # Generate question
                question = await self.question_agent.generate_question(
                    case.design_purpose,
                    qa_history
                )
                
                # Generate answer
                answer = await self.answer_agent.generate_answer(
                    case.data_practice,
                    question
                )
                
                # Record QA pair
                qa_pair = QAPair(
                    question=question,
                    answer=answer,
                    timestamp=datetime.now().isoformat()
                )
                qa_history.append(qa_pair)
                
                # Print progress
                print(f"\nAnalyzing case: {case.case_name}")
                print(f"Q{len(qa_history)}: {question.text}")
                print(f"Options: {question.options}")
                print(f"Selected Options: {answer.selected_options}")
                print(f"A{len(qa_history)}: {answer.explanation}")
                print("-" * 80)
                
            return qa_history
            
        except Exception as e:
            print(f"Error in analysis: {e}")
            raise

    def save_case_results(self, case_name: str, qa_history: List[QAPair], output_dir: str = "results"):
        """Save QA history for a single case to a JSON file"""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        results = []
        for qa in qa_history:
            results.append({
                "question": {
                    "text": qa.question.text,
                    "options": qa.question.options,
                    "category": qa.question.category
                },
                "answer": {
                    "selected_options": qa.answer.selected_options,
                    "explanation": qa.answer.explanation
                },
                "timestamp": qa.timestamp
            })
        
        filename = os.path.join(output_dir, f"{case_name}_[BASE].json")
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)

async def load_cases(csv_file: str) -> List[CaseData]:
    """Load cases from CSV file"""
    cases = []
    df = pd.read_csv(csv_file)
    
    for _, row in df.iterrows():
        case = CaseData(
            case_name=row['Case'],
            design_purpose=row['Design Purpose'],
            data_practice=row['Data Practice'],
            key_questions=row['Key Questions']
        )
        cases.append(case)
    
    return cases

async def main():
    # Get API key
    api_key = os.getenv("OPENAI_API_KEY")
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.getenv("api_key")
    if not api_key:
        raise ValueError("Please set OPENAI_API_KEY environment variable")
    
    # Load cases from CSV
    cases = await load_cases('privacy_cases.csv')
    
    # Initialize analyzer
    analyzer = PrivacyAnalyzer(api_key)
    
    # Process each case
    for case in cases:
        try:
            print(f"\nProcessing case: {case.case_name}")
            qa_history = await analyzer.analyze_case(case)
            analyzer.save_case_results(case.case_name, qa_history)
            print(f"Completed case: {case.case_name}")
        except Exception as e:
            print(f"Error processing case {case.case_name}: {e}")
            continue

    print("\nAll cases processed.")

if __name__ == "__main__":
    asyncio.run(main())