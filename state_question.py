from enum import Enum
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
import json
from datetime import datetime
import asyncio
import pandas as pd
from openai import AsyncOpenAI
import os

class PrivacyDimension(Enum):
    COLLECTION_LIMITATION = "Collection Limitation"
    DATA_QUALITY = "Data Quality"
    PURPOSE_SPECIFICATION = "Purpose Specification"
    USE_LIMITATION = "Use Limitation"
    SECURITY_SAFEGUARDS = "Security Safeguards"
    OPENNESS = "Openness"
    INDIVIDUAL_PARTICIPATION = "Individual Participation"
    ACCOUNTABILITY = "Accountability"

@dataclass
class PredefinedQuestion:
    stage: str
    category: str
    key: str
    question: str
    property: str
    dimensions: List[str] = field(default_factory=list)

@dataclass
class Question:
    text: str
    options: List[Dict[str, str]]
    category: str
    target_dimension: Optional[str] = None

@dataclass
class Answer:
    selected_options: List[str]
    explanation: str

@dataclass
class QAPair:
    question: Question
    answer: Answer
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class StateChange:
    original: str
    now: str
    reasoning: str = ""

    def to_dict(self) -> Dict:
        """Convert StateChange to dictionary for JSON serialization"""
        return {
            "original": self.original,
            "now": self.now,
            "reasoning": self.reasoning
        }

class StateTracker:
    def __init__(self):
        self.questions = []
        self.question_count = 0
        self.start_state = {}
        self.current_state = {}
        self.final_state = {}
        self.state_changes = {}  # Track state changes with reasoning

    def set_initial_states(self, initial_states: Dict[str, Dict]):
        """Set the initial states of all dimensions"""
        self.start_state = initial_states
        self.current_state = initial_states.copy()
        # Initialize state changes tracking
        self.state_changes = {dim: [] for dim in initial_states.keys()}

    def set_final_states(self, final_states: Dict[str, Dict]):
        """Set the final states after analysis is complete"""
        self.final_state = final_states.copy()  # Make a copy to ensure independence
        
        # Add a final state change record for any dimensions that changed
        for dimension, state_info in final_states.items():
            current_state = self.current_state.get(dimension, {}).get("state", "")
            final_state = state_info.get("state", "")
            
            if current_state != final_state:
                self.state_changes[dimension].append(
                    StateChange(
                        original=current_state,
                        now=final_state,
                        reasoning="Final state determination at analysis completion"
                    )
                )

    def add_question(self, qa_pair: QAPair):
        """Add a question with target dimension and state changes"""
        self.question_count += 1
        
        # Get the target dimension's states
        target_dim = qa_pair.question.target_dimension
        target_state_change = {
            "original": self.current_state.get(target_dim, {}).get("state", "Potential Issue"),
            "now": self.current_state.get(target_dim, {}).get("state", "Potential Issue"),
            "reasoning": ""  # Will be updated when state changes
        } if target_dim else None
        
        question_state = {
            "id": str(self.question_count),
            "question": {
                "text": qa_pair.question.text,
                "options": qa_pair.question.options,
            },
            "selectedOptions": qa_pair.answer.selected_options,
            "explanation": qa_pair.answer.explanation,
            "target_dimension": target_dim,
            "target_dimension_state": target_state_change
        }
        
        self.questions.append(question_state)

    def update_dimension_state(self, dimension: str, new_state: str, reasoning: str = ""):
        """Update a dimension's state and record the change with reasoning"""
        if dimension in self.current_state:
            old_state = self.current_state[dimension]["state"]
            
            # Record state change with reasoning
            state_change = StateChange(
                original=old_state,
                now=new_state,
                reasoning=reasoning
            )
            self.state_changes[dimension].append(state_change)
            
            # Update the last question's target dimension state if it matches
            if self.questions and self.questions[-1]["target_dimension"] == dimension:
                self.questions[-1]["target_dimension_state"].update({
                    "now": new_state,
                    "reasoning": reasoning
                })
            
            # Update current state
            self.current_state[dimension]["state"] = new_state
            self.current_state[dimension]["latest_reasoning"] = reasoning

    def get_dimension_history(self, dimension: str) -> List[Dict]:
        """Get the complete history of state changes for a dimension"""
        return [
            change.to_dict()  # Use to_dict() method instead of direct conversion
            for change in self.state_changes.get(dimension, [])
        ]

    def to_json(self) -> Dict:
        # Convert state changes to serializable format using to_dict()
        serialized_changes = {}
        for dim, changes in self.state_changes.items():
            serialized_changes[dim] = [
                change.to_dict()  # Use to_dict() method for serialization
                for change in changes
            ]

        return {
            "start_state": self.start_state,
            "questions": self.questions,
            "final_state": self.final_state,
            "state_changes": serialized_changes
        }

class BaseQuestionPhase:
    def __init__(self, client: AsyncOpenAI):
        self.client = client
        self.predefined_questions = self._load_predefined_questions()

    def _load_predefined_questions(self) -> List[PredefinedQuestion]:
        try:
            df = pd.read_csv('question_list.csv', encoding='utf-8')
            df = df[df['Question'].notna()]
            
            questions = []
            for _, row in df.iterrows():
                question = PredefinedQuestion(
                    stage=row['Stage'] if not pd.isna(row['Stage']) else "",
                    category=row['Category'] if not pd.isna(row['Category']) else "",
                    key=row['Key'] if not pd.isna(row['Key']) else "",
                    question=row['Question'],
                    property=row['Property'] if not pd.isna(row['Property']) else "",
                    dimensions=[]
                )
                questions.append(question)
            
            return questions
            
        except Exception as e:
            print(f"Error loading predefined questions: {e}")
            raise

    async def select_relevant_questions(self, design_purpose: str) -> List[PredefinedQuestion]:
        questions_context = "\n".join([
            f"- {q.question} (Stage: {q.stage}, Category: {q.category})"
            for q in self.predefined_questions
        ])

        system_prompt = f"""You are a Privacy Question Selector.
Your task is to select the 10 most relevant questions from the provided list based on the given design purpose.

Design Purpose: {design_purpose}

Available Questions:
{questions_context}

Select questions that:
1. Are most relevant to understanding the privacy implications of this design purpose
2. Cover different aspects of privacy (collection, processing, storage, sharing, etc.)
3. Are fundamental to understanding the privacy practices

Return in JSON format:
{{
    "selected_questions": [
        {{
            "question_text": "Original question text from the list",
            "relevance_explanation": "Why this question is relevant",
            "target_dimension": "Primary privacy dimension this addresses"
        }}
    ]
}}"""

        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": system_prompt}],
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        selected_questions = []
        
        for selected in result["selected_questions"]:
            for predefined in self.predefined_questions:
                if predefined.question == selected["question_text"]:
                    predefined.dimensions = [selected["target_dimension"]]
                    selected_questions.append(predefined)
                    break
        
        return selected_questions[:10]

    async def generate_contextualized_questions(
        self,
        selected_questions: List[PredefinedQuestion],
        design_purpose: str,
        data_practice: str
    ) -> List[Question]:
        selected_context = "\n".join([
            f"- {q.question} (Stage: {q.stage}, Category: {q.category}, Dimension: {q.dimensions[0] if q.dimensions else 'None'})"
            for q in selected_questions
        ])

        system_prompt = f"""You are a Privacy Question Generator.
Your task is to adapt the selected questions to the specific context and generate appropriate options.

Design Purpose: {design_purpose}

Data Practice:
{data_practice}

Selected Questions:
{selected_context}

For each question:
1. Adapt it to the specific context while maintaining its original intent
2. Generate 4-5 detailed multiple choice options
3. Ensure options are distinct and comprehensive

Return in JSON format:
{{
    "questions": [
        {{
            "text": "Contextualized question text",
            "options": [
                {{"id": "option1", "label": "Detailed option 1"}},
                {{"id": "option2", "label": "Detailed option 2"}},
                {{"id": "option3", "label": "Detailed option 3"}},
                {{"id": "option4", "label": "Detailed option 4"}}
            ],
            "category": "Question category",
            "target_dimension": "Primary privacy dimension"
        }}
    ]
}}"""

        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": system_prompt}],
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return [
            Question(
                text=q["text"],
                options=q["options"],
                category=q["category"],
                target_dimension=q["target_dimension"]
            )
            for q in result["questions"]
        ]

class AnswerGenerator:
    def __init__(self, client: AsyncOpenAI):
        self.client = client

    async def generate_answer(self, data_practice: str, question: Question) -> Answer:
        """Generate answer for a question"""
        system_prompt = f"""You are a Privacy Answer Generator.
Your task is to analyze the data practice and select appropriate answers to the privacy question.

Data Practice:
{data_practice}

Current Question: {question.text}
Available Options:
{json.dumps(question.options, indent=2)}

Provide an answer that:
1. Reflects the actual practices described in the data practice
2. Is supported by specific details from the data practice
3. Provides a clear explanation for the selection

Return in JSON format:
{{
    "selected_options": ["option1"],
    "explanation": "Detailed explanation of why these options were selected"
}}"""

        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": system_prompt}],
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return Answer(
            selected_options=result["selected_options"],
            explanation=result["explanation"]
        )

class BasePhaseAnalyzer:
    def __init__(self, client: AsyncOpenAI):
        self.client = client

    async def analyze_qa_pairs(self, qa_pairs: List[QAPair], design_purpose: str) -> Dict[str, Dict]:
        """Analyze base QA pairs to determine initial dimension states"""
        qa_context = "\n".join([
            f"Q: {qa.question.text}\n"
            f"A: Selected: {qa.answer.selected_options}\n"
            f"Explanation: {qa.answer.explanation}\n"
            f"---"
            for qa in qa_pairs
        ])

        system_prompt = f"""You are a Privacy State Analyzer.
Your task is to analyze the base question-answer pairs and determine initial states for each privacy dimension.

Design Purpose: {design_purpose}

QA History:
{qa_context}

For each privacy dimension (Collection Limitation, Data Quality, Purpose Specification, 
Use Limitation, Security Safeguards, Openness, Individual Participation, Accountability):
1. Determine initial state (No Issue/Has Issue/Potential Issue)
2. Provide reasoning for the state
3. Identify areas needing investigation
4. If without enough information, mark as Potential Issue
5. The has issue  state should have enough information to justify the issue

Return in JSON format:
{{
    "dimension_states": {{
        "dimension_name": {{
            "state": "No Issue/Has Issue/Potential Issue",
            "description": "Reasoning for initial state",
            "areas_to_investigate": ["Specific aspect 1", "Specific aspect 2"]
        }}
    }}
}}"""

        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": system_prompt}],
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)["dimension_states"]

class FollowUpPhaseAnalyzer:
    def __init__(self, client: AsyncOpenAI):
        self.client = client

    async def generate_follow_up_question(
        self,
        current_states: Dict[str, Dict],
        qa_history: List[QAPair],
        design_purpose: str,
        state_changes: Dict[str, List[StateChange]]  # Type hint updated
    ) -> Question:
        """Generate follow-up question for potential issues"""
        potential_issues = {
            dim: info for dim, info in current_states.items()
            if info["state"] == "Potential Issue"
        }
        
        # Convert StateChange objects to dictionaries for serialization
        serialized_changes = {
            dim: [change.to_dict() for change in changes]
            for dim, changes in state_changes.items()
        }
        
        qs_context = "\n".join([
            f"- {qa.question.text} (Selected Answer: {qa.answer.selected_options[0]})"
            for qa in qa_history
        ]) if qa_history else "No previous questions"
        print(qs_context)
        state_context = "\n".join([
            f"Dimension: {dim}\n"
            f"Current State: {info['state']}\n"
            f"Description: {info['description']}\n"
            f"Areas to Investigate: {info.get('areas_to_investigate', [])}\n"
            f"State Change History: {json.dumps(serialized_changes.get(dim, []), indent=2)}\n"
            f"---"
            for dim, info in potential_issues.items()
        ])

        system_prompt = f"""You are a Privacy Follow-up Question Generator.
Your task is to generate a targeted question for a dimension that needs investigation.

Current Potential Issues:
{state_context}

QA History:
{qs_context}
Generate a question that:
1. Targets one specific dimension with potential issues
2. Addresses one of its areas needing investigation
3. Takes into account the previous state changes and their reasoning
4. Will help determine if there is a real issue
5. Has 4-5 clear answer options

Return in JSON format:
{{
    "question": {{
        "text": "Question text",
        "options": [
            {{"id": "option1", "label": "Detailed option 1"}},
            {{"id": "option2", "label": "Detailed option 2"}},
            {{"id": "option3", "label": "Detailed option 3"}},
            {{"id": "option4", "label": "Detailed option 4"}}
        ],
        "target_dimension": "Selected dimension name",
        "investigation_focus": "What aspect this question investigates"
    }}
}}"""

        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": system_prompt}],
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)["question"]
        return Question(
            text=result["text"],
            options=result["options"],
            category="follow_up",
            target_dimension=result["target_dimension"]
        )

    async def analyze_impact(
        self,
        qa_pair: QAPair,
        current_states: Dict[str, Dict],
        state_changes: Dict[str, List[StateChange]]  # Type hint updated
    ) -> Tuple[str, str]:
        """Analyze how a follow-up answer impacts the target dimension"""
        target_dim = qa_pair.question.target_dimension
        current_state = current_states[target_dim]
        
        # Convert StateChange objects to dictionaries for serialization
        change_history = [
            change.to_dict() 
            for change in state_changes.get(target_dim, [])
        ]

        system_prompt = f"""You are a Privacy Impact Analyzer.
Your task is to analyze how this answer affects the target dimension's state.

Target Dimension: {target_dim}
Current State: {current_state['state']}
Current Description: {current_state['description']}
State Change History: {json.dumps(change_history, indent=2)}

Question: {qa_pair.question.text}
Selected Options: {qa_pair.answer.selected_options}
Explanation: {qa_pair.answer.explanation}

Determine:
1. Whether this answer changes the dimension's state
2. Consider the previous state changes and their reasoning
3. Justify any state change in the context of the history

Return in JSON format:
{{
    "new_state": "No Issue/Has Issue/Potential Issue",
    "reasoning": "Detailed explanation of state determination"
}}"""

        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": system_prompt}],
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return result["new_state"], result["reasoning"]

class PrivacyAnalyzer:
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)
        self.base_phase = BaseQuestionPhase(self.client)
        self.base_analyzer = BasePhaseAnalyzer(self.client)
        self.follow_up_phase = FollowUpPhaseAnalyzer(self.client)
        self.answer_generator = AnswerGenerator(self.client)
        self.state_tracker = StateTracker()

    async def analyze(self, design_purpose: str, data_practice: str) -> Dict:
        """Run complete privacy analysis"""
        try:
            # Phase 1: Base Questions
            print("\nPhase 1: Processing base questions...")
            qa_pairs = []
            
            # Get and process base questions
            selected_questions = await self.base_phase.select_relevant_questions(design_purpose)
            print(f"Selected {len(selected_questions)} relevant questions")
            
            contextualized_questions = await self.base_phase.generate_contextualized_questions(
                selected_questions,
                design_purpose,
                data_practice
            )
            
            # Process base questions
            for question in contextualized_questions:
                answer = await self.answer_generator.generate_answer(
                    data_practice,
                    question
                )
                
                qa_pair = QAPair(question=question, answer=answer)
                self.state_tracker.add_question(qa_pair)
                qa_pairs.append(qa_pair)
                
                print(f"\nProcessed base question: {question.text[:100]}...")

            # Initialize dimension states based on base answers
            print("\nAnalyzing base answers to determine dimension states...")
            initial_states = await self.base_analyzer.analyze_qa_pairs(
                qa_pairs,
                design_purpose
            )
            self.state_tracker.set_initial_states(initial_states)

            # Phase 2: Follow-up Questions
            print("\nPhase 2: Processing follow-up questions...")
            max_follow_ups = 15
            follow_up_count = 0
            
            while follow_up_count < max_follow_ups:
                potential_issues = [
                    dim for dim, info in self.state_tracker.current_state.items()
                    if info["state"] == "Potential Issue"
                ]
                
                if not potential_issues:
                    print("Analysis complete - no potential issues remain")
                    break

                # Get state changes for follow-up question generation
                question = await self.follow_up_phase.generate_follow_up_question(
                    self.state_tracker.current_state,
                    qa_pairs,
                    design_purpose,
                    self.state_tracker.state_changes  # Pass state changes history
                )
                
                answer = await self.answer_generator.generate_answer(
                    data_practice,
                    question
                )
                
                qa_pair = QAPair(question=question, answer=answer)
                
                # Analyze impact with state changes history
                new_state, reasoning = await self.follow_up_phase.analyze_impact(
                    qa_pair,
                    self.state_tracker.current_state,
                    self.state_tracker.state_changes  # Pass state changes history
                )
                
                # Update state tracking with reasoning
                self.state_tracker.add_question(qa_pair)
                self.state_tracker.update_dimension_state(
                    question.target_dimension,
                    new_state,
                    reasoning
                )
                
                qa_pairs.append(qa_pair)
                follow_up_count += 1
                
                print(f"\nProcessed follow-up question {follow_up_count} for {question.target_dimension}")
                print(f"New state: {new_state} - {reasoning[:100]}...")

                if follow_up_count >= max_follow_ups:
                    print("Reached maximum follow-up questions limit")
                    break

            # Set final states
            self.state_tracker.set_final_states(self.state_tracker.current_state)
            return self.state_tracker.to_json()

        except Exception as e:
            print(f"Error in privacy analysis: {e}")
            raise

    def save_results(self, case_name: str, results: Dict, output_dir: str = "results"):
        """Save analysis results to files"""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        filename = os.path.join(output_dir, f"{case_name}_analysis.json")
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)

async def main():
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Please set OPENAI_API_KEY environment variable")

    # Load cases
    cases_df = pd.read_csv("privacy_cases.csv")
    
    # Initialize analyzer
    analyzer = PrivacyAnalyzer(api_key)
    
    # Process each case
    for _, case in cases_df.iterrows():
        print(f"\nProcessing case: {case['Case']}")
        results = await analyzer.analyze(
            case['Design Purpose'],
            case['Data Practice']
        )
        analyzer.save_results(case['Case'], results)
        print(f"Completed case: {case['Case']}")
        

    print("\nAll cases processed.")

if __name__ == "__main__":
    asyncio.run(main())