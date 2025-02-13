import os
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import json
import asyncio
from openai import AsyncOpenAI, OpenAI

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

class QuestionAgent:
    def __init__(self, client: AsyncOpenAI):
        self.client = client

    async def generate_question(self, design_purpose: str, qa_history: List[QAPair]) -> Question:
        # Format conversation history
        history_str = "\n".join([
            f"Q{i+1}: {qa.question.text}\nA{i+1}: {qa.answer.explanation}"
            for i, qa in enumerate(qa_history)
        ])
        
        # Create the system prompt
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
                model="gpt-4o",
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
        # Create the system prompt
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
                model="gpt-4o",
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
        self.qa_history: List[QAPair] = []

    async def analyze(self, design_purpose: str, data_practice: str, max_pairs: int = 25) -> List[QAPair]:
        """Run the complete privacy analysis"""
        try:
            while len(self.qa_history) < max_pairs:
                # Generate question
                question = await self.question_agent.generate_question(
                    design_purpose,
                    self.qa_history
                )
                
                # Generate answer
                answer = await self.answer_agent.generate_answer(
                    data_practice,
                    question
                )
                
                # Record QA pair
                qa_pair = QAPair(
                    question=question,
                    answer=answer,
                    timestamp=datetime.now().isoformat()
                )
                self.qa_history.append(qa_pair)
                
                # Print progress
                print(f"\nQ{len(self.qa_history)}: {question.text}")
                print(f"Options: {question.options}")
                print(f"Selected Options: {answer.selected_options}")
                print(f"A{len(self.qa_history)}: {answer.explanation}")
                print("-" * 80)
                
            return self.qa_history
            
        except Exception as e:
            print(f"Error in analysis: {e}")
            raise

    def save_results(self, filename: str):
        """Save QA history to a JSON file"""
        results = []
        for qa in self.qa_history:
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
            
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)

async def main():
    # Get API key from environment variable
    api_key = os.getenv("OPENAI_API_KEY")
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.getenv("api_key")
    if not api_key:
        raise ValueError("Please set OPENAI_API_KEY environment variable")
    
    # Example inputs
    design_purpose = """
    Design an attendee attention tracking feature for a video conferencing application.
    """
    
    data_practice = """
   Zoom is a video conferencing platform which has seen a huge increase in usage and revenue since the beginning of the COVID-19 pandemic 
   and has rapidly iterated its product to accommodate this growing user base. Zoom developed a feature that allowed the host to monitor the 
   attendees’ attention: if Zoom was not the application in focus on a participant's computer for over 30 seconds while someone else was
     sharing their screen, Zoom showed a clock icon next to the participant's name in the participant panel. At the end of each meeting, 
    Zoom also generated a report for the host listing the percentage of time each participant had the presentation window in focus during 
    the meeting. This feature received significant backlash after launch. The Zoom team later apologized for falling short of the community's privacy and security expectations and decided to remove the attention tracker feature permanently.
    """
    
    # Initialize and run analyzer
    analyzer = PrivacyAnalyzer(api_key)
    qa_history = await analyzer.analyze(design_purpose, data_practice)
    
    # Save results
    analyzer.save_results("privacy_analysis_results.json")
    print(f"\nAnalysis complete. Generated {len(qa_history)} Q&A pairs.")

if __name__ == "__main__":
    asyncio.run(main())