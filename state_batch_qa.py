import os
from enum import Enum
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass, field
import json
from datetime import datetime
import asyncio
import pandas as pd
from openai import AsyncOpenAI

# Core Data Structures
class PrivacyDimension(Enum):
    COLLECTION_LIMITATION = "Collection Limitation"
    DATA_QUALITY = "Data Quality"
    PURPOSE_SPECIFICATION = "Purpose Specification"
    USE_LIMITATION = "Use Limitation"
    SECURITY_SAFEGUARDS = "Security Safeguards"
    OPENNESS = "Openness"
    INDIVIDUAL_PARTICIPATION = "Individual Participation"
    ACCOUNTABILITY = "Accountability"

class DimensionState(Enum):
    NO_ISSUE = "No Issue"
    HAS_ISSUE = "Has Issue"
    POTENTIAL_ISSUE = "Potential Issue"

@dataclass
class PredefinedQuestion:
    stage: str
    category: str
    key: str
    question: str
    property: str
    dimensions: List[str]

@dataclass
class Question:
    text: str
    options: List[Dict[str, str]]
    category: str
    related_dimensions: List[PrivacyDimension] = field(default_factory=list)

@dataclass
class Answer:
    selected_options: List[str]
    explanation: str
    impact_analysis: Dict[PrivacyDimension, str] = field(default_factory=dict)

@dataclass
class QAPair:
    question: Question
    answer: Answer
    timestamp: str

@dataclass
class PrivacyConcern:
    dimension: PrivacyDimension
    description: str
    reasoning: str
    related_questions: List[str]
    timestamp: str

@dataclass
class DimensionStatus:
    state: DimensionState
    concerns: List[PrivacyConcern]
    potential_questions: List[str]

# Base Question Phase
class BaseQuestionPhase:
    def __init__(self, client: AsyncOpenAI):
        self.client = client
        self.predefined_questions = self._load_predefined_questions()

    def _load_predefined_questions(self) -> List[PredefinedQuestion]:
        """Load predefined questions from CSV file"""
        try:
            df = pd.read_csv('question_list.csv', encoding='utf-8')
            df = df[df['Question'].notna()]  # Only remove truly empty rows
            
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
            
            print(f"Loaded {len(questions)} predefined questions")
            return questions
            
        except Exception as e:
            print(f"Error loading predefined questions: {e}")
            raise

    async def select_relevant_questions(self, design_purpose: str) -> List[PredefinedQuestion]:
        """Select most relevant questions based on design purpose"""
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
            "relevance_explanation": "Why this question is relevant"
        }}
    ]
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
            selected_texts = [q["question_text"] for q in result["selected_questions"]]
            
            # Find the original question objects
            selected_questions = [
                q for q in self.predefined_questions 
                if q.question in selected_texts
            ]
            
            return selected_questions[:10]
            
        except Exception as e:
            print(f"Error selecting relevant questions: {e}")
            raise

    async def generate_contextualized_questions(
        self,
        selected_questions: List[PredefinedQuestion],
        design_purpose: str,
        data_practice: str
    ) -> List[Question]:
        """Generate contextualized questions with options"""
        
        selected_context = "\n".join([
            f"- {q.question} (Stage: {q.stage}, Category: {q.category})"
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
2. Generate 3-5 multiple choice options that cover possible answers
3. Ensure options cover different aspects of privacy practices

Return in JSON format:
{{
    "questions": [
        {{
            "text": "Contextualized question text",
            "options": [
                {{"id": "option1", "label": "Option 1 description"}},
                {{"id": "option2", "label": "Option 2 description"}}
            ],
            "category": "Original question category"
        }}
    ]
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
            return [
                Question(
                    text=q["text"],
                    options=q["options"],
                    category=q["category"]
                )
                for q in result["questions"]
            ]
            
        except Exception as e:
            print(f"Error generating contextualized questions: {e}")
            raise

    async def process_base_phase(
        self,
        design_purpose: str,
        data_practice: str
    ) -> List[QAPair]:
        """Process the complete base question phase"""
        # 1. Select relevant questions
        selected_questions = await self.select_relevant_questions(design_purpose)
        
        # 2. Generate contextualized questions
        contextualized_questions = await self.generate_contextualized_questions(
            selected_questions,
            design_purpose,
            data_practice
        )
        
        # 3. Generate answers (without dimension analysis)
        answer_generator = AnswerGenerator(self.client)
        qa_pairs = []
        
        for question in contextualized_questions:
            answer = await answer_generator.generate_base_answer(
                data_practice,
                question
            )
            
            qa_pair = QAPair(
                question=question,
                answer=answer,
                timestamp=datetime.now().isoformat()
            )
            qa_pairs.append(qa_pair)
        
        return qa_pairs

# Answer Generation
class AnswerGenerator:
    def __init__(self, client: AsyncOpenAI):
        self.client = client

    async def generate_base_answer(self, data_practice: str, question: Question) -> Answer:
        """Generate answer for base phase questions (without dimension analysis)"""
        system_prompt = f"""You are a Privacy Answer Generator.
Your task is to analyze the data practice and select appropriate answers to the privacy question.

Data Practice:
{data_practice}

Current Question: {question.text}
Available Options:
{json.dumps(question.options, indent=2)}

Provide an answer that:
1. Reflects the actual practices described in the data practice
2. Considers privacy implications and user expectations
3. Is supported by specific details from the data practice

Return in JSON format:
{{
    "selected_options": ["option1", "option2"],
    "explanation": "Detailed explanation of why these options were selected based on the data practice"
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
            print(f"Error generating base answer: {e}")
            raise

    async def generate_answer(self, data_practice: str, question: Question) -> Answer:
        """Generate answer with dimension analysis"""
        system_prompt = f"""You are a Privacy Answer Generator.
Your task is to analyze the data practice and select appropriate answers to the privacy question.

Data Practice:
{data_practice}

Current Question: {question.text}
Available Options:
{json.dumps(question.options, indent=2)}

Related Dimensions: {[d.value for d in question.related_dimensions]}

Provide an answer that:
1. Reflects the actual practices described in the data practice
2. Considers privacy implications for each related dimension
3. Is supported by specific details from the data practice

Return in JSON format:
{{
    "selected_options": ["option1", "option2"],
    "explanation": "Detailed explanation of selection",
    "dimension_impacts": {{
        "dimension_name": "Analysis of how this answer impacts this dimension"
    }}
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
                explanation=result["explanation"],
                impact_analysis={
                    PrivacyDimension(dim): impact
                    for dim, impact in result["dimension_impacts"].items()
                }
            )
            
        except Exception as e:
            print(f"Error generating answer: {e}")
            raise

# Dimension Analysis Phase
class DimensionAnalysisPhase:
    def __init__(self, client: AsyncOpenAI):
        self.client = client

    async def initialize_state(self, base_qa_pairs: List[QAPair]) -> Dict[PrivacyDimension, DimensionStatus]:
        """Initialize dimension states based on base QA pairs"""
        
        # Format QA context
        qa_context = "\n".join([
            f"Q: {qa.question.text}\nA: {qa.answer.explanation}"
            for qa in base_qa_pairs
        ])
        #with open fipp.txt import the definition of the privacy dimensions
        with open('fipp.txt') as f:
            fipp = f.read()
        
            
        system_prompt = f"""You are a Privacy State Analyzer.
Your task is to analyze the initial QA pairs and determine the state of each privacy dimension.

Previous QA History:
{qa_context}

Privacy Dimensions:
{fipp}
For each privacy dimension (Collection Limitation, Data Quality, Purpose Specification, Use Limitation, 
Security Safeguards, Openness, Individual Participation, Accountability), determine:
1. Current state (No Issue/Has Issue/Potential Issue)
2. Any identified concerns
3. Potential questions that need to be asked

Return in JSON format:
{{
    "dimension_states": {{
        "dimension_name": {{
            "state": "No Issue/Has Issue/Potential Issue",
            "concerns": [
                {{
                    "description": "Description of concern",
                    "reasoning": "Reasoning behind the concern",
                    "related_questions": ["Potential follow-up question 1", "..."]
                }}
            ],
            "potential_questions": ["Question 1", "Question 2"]
        }}
    }}
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
            
            # Convert to dimension states
            dimension_states = {}
            for dim in PrivacyDimension:
                dim_data = result["dimension_states"][dim.value]
                
                # Convert concerns
                concerns = []
                for concern_data in dim_data.get("concerns", []):
                    concern = PrivacyConcern(
                        dimension=dim,
                        description=concern_data["description"],
                        reasoning=concern_data["reasoning"],
                        related_questions=concern_data["related_questions"],
                        timestamp=datetime.now().isoformat()
                    )
                    concerns.append(concern)
                
                # Create dimension status
                status = DimensionStatus(
                    state=DimensionState[dim_data["state"].replace(" ", "_")],
                    concerns=concerns,
                    potential_questions=dim_data.get("potential_questions", [])
                )
                dimension_states[dim] = status
            
            return dimension_states
            
        except Exception as e:
            print(f"Error initializing dimension states: {e}")
            raise

    async def generate_follow_up_question(
        self,
        dimension_states: Dict[PrivacyDimension, DimensionStatus],
        qa_history: List[QAPair],
        design_purpose: str,
        data_practice: str
    ) -> Question:
        """Generate follow-up question based on current state"""
        
        # Format current state
        state_context = "\n".join([
            f"Dimension: {dim.value}\n"
            f"State: {status.state.value}\n"
            f"Concerns: {[c.description for c in status.concerns]}\n"
            f"Potential Questions: {status.potential_questions}\n"
            f"---"
            for dim, status in dimension_states.items()
        ])

        # Format QA history
        qa_context = "\n".join([
            f"Q: {qa.question.text}\nA: {qa.answer.explanation}"
            for qa in qa_history
        ])

        system_prompt = f"""You are a Privacy Follow-up Question Generator.
Your task is to generate the next question based on the current state of privacy dimensions.

Design Purpose: {design_purpose}

Data Practice: {data_practice}

Current State of Dimensions:
{state_context}

Previous QA History:
{qa_context}

Generate a follow-up question that:
1. Addresses the most critical potential issues or concerns
2. Helps determine if there are actual privacy issues
3. Has clear implications for specific privacy dimensions
4. Will help move dimensions from "Potential Issue" to either "Has Issue" or "No Issue"

Return in JSON format:
{{
    "question": {{
        "text": "Question text",
        "options": [
            {{"id": "option1", "label": "Option 1 description"}},
            {{"id": "option2", "label": "Option 2 description"}}
        ],
        "category": "question_category",
        "related_dimensions": ["dimension1", "dimension2"],
        "reasoning": "Why this question is important now"
    }}
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
            q_data = result["question"]
            
            return Question(
                text=q_data["text"],
                options=q_data["options"],
                category=q_data["category"],
                related_dimensions=[PrivacyDimension(dim) for dim in q_data["related_dimensions"]]
            )
            
        except Exception as e:
            print(f"Error generating follow-up question: {e}")
            raise
    def _convert_state_string(self, state_str: str) -> DimensionState:
        """Convert state string to DimensionState enum value"""
        # Clean up the state string
        state_str = state_str.strip().upper().replace(" ", "_")
        
        # Map from various possible strings to enum values
        state_mapping = {
            "NO_ISSUE": DimensionState.NO_ISSUE,
            "HAS_ISSUE": DimensionState.HAS_ISSUE,
            "POTENTIAL_ISSUE": DimensionState.POTENTIAL_ISSUE,
            # Add common variations
            "NO ISSUE": DimensionState.NO_ISSUE,
            "HAS ISSUE": DimensionState.HAS_ISSUE,
            "POTENTIAL ISSUE": DimensionState.POTENTIAL_ISSUE,
        }
        
        if state_str not in state_mapping:
            print(f"Warning: Unknown state string '{state_str}', defaulting to POTENTIAL_ISSUE")
            return DimensionState.POTENTIAL_ISSUE
            
        return state_mapping[state_str]

    async def initialize_state(self, base_qa_pairs: List[QAPair]) -> Dict[PrivacyDimension, DimensionStatus]:
        """Initialize dimension states based on base QA pairs"""
        
        # Format QA context
        qa_context = "\n".join([
            f"Q: {qa.question.text}\nA: {qa.answer.explanation}"
            for qa in base_qa_pairs
        ])

        system_prompt = f"""You are a Privacy State Analyzer.
Your task is to analyze the initial QA pairs and determine the state of each privacy dimension.

Previous QA History:
{qa_context}

For each privacy dimension (Collection Limitation, Data Quality, Purpose Specification, Use Limitation, 
Security Safeguards, Openness, Individual Participation, Accountability), determine:
1. Current state (must be exactly one of: "No Issue", "Has Issue", "Potential Issue")
2. Any identified concerns
3. Potential questions that need to be asked

Return in JSON format:
{{
    "dimension_states": {{
        "dimension_name": {{
            "state": "No Issue/Has Issue/Potential Issue",
            "concerns": [
                {{
                    "description": "Description of concern",
                    "reasoning": "Reasoning behind the concern",
                    "related_questions": ["Potential follow-up question 1", "..."]
                }}
            ],
            "potential_questions": ["Question 1", "Question 2"]
        }}
    }}
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
            
            # Convert to dimension states
            dimension_states = {}
            for dim in PrivacyDimension:
                dim_data = result["dimension_states"].get(dim.value, {
                    "state": "Potential Issue",
                    "concerns": [],
                    "potential_questions": []
                })
                
                # Convert concerns
                concerns = []
                for concern_data in dim_data.get("concerns", []):
                    concern = PrivacyConcern(
                        dimension=dim,
                        description=concern_data["description"],
                        reasoning=concern_data["reasoning"],
                        related_questions=concern_data["related_questions"],
                        timestamp=datetime.now().isoformat()
                    )
                    concerns.append(concern)
                
                # Create dimension status with state conversion
                status = DimensionStatus(
                    state=self._convert_state_string(dim_data["state"]),
                    concerns=concerns,
                    potential_questions=dim_data.get("potential_questions", [])
                )
                dimension_states[dim] = status
            
            return dimension_states
            
        except Exception as e:
            print(f"Error initializing dimension states: {e}")
            raise

    async def analyze_answer_impact(
        self,
        qa_pair: QAPair,
        current_states: Dict[PrivacyDimension, DimensionStatus]
    ) -> Tuple[Dict[PrivacyDimension, DimensionStatus], List[PrivacyConcern]]:
        """Analyze how an answer impacts dimension states"""
        
        # Format current state
        state_context = "\n".join([
            f"Dimension: {dim.value}\n"
            f"State: {status.state.value}\n"
            f"Concerns: {[c.description for c in status.concerns]}\n"
            f"---"
            for dim, status in current_states.items()
        ])

        system_prompt = f"""You are a Privacy Impact Analyzer.
Your task is to analyze how this answer impacts the state of privacy dimensions.

Question: {qa_pair.question.text}
Selected Options: {qa_pair.answer.selected_options}
Explanation: {qa_pair.answer.explanation}

Current States:
{state_context}

Analyze:
1. How this answer affects each related dimension
2. Whether it resolves or creates new concerns
3. Whether dimension states should change
4. What follow-up questions might be needed

For states, use exactly one of: "No Issue", "Has Issue", "Potential Issue"

Return in JSON format:
{{
    "impacts": {{
        "dimension_name": {{
            "new_state": "No Issue/Has Issue/Potential Issue",
            "analysis": "How this answer impacts this dimension",
            "concerns": [
                {{
                    "description": "Concern description",
                    "reasoning": "Why this is a concern",
                    "related_questions": ["Follow-up question 1", "..."]
                }}
            ]
        }}
    }}
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
            
            # Update states and collect new concerns
            new_states = current_states.copy()
            new_concerns = []
            
            for dim_name, impact in result["impacts"].items():
                dimension = PrivacyDimension(dim_name)
                new_state = self._convert_state_string(impact["new_state"])
                
                # Create new concerns
                for concern_data in impact.get("concerns", []):
                    concern = PrivacyConcern(
                        dimension=dimension,
                        description=concern_data["description"],
                        reasoning=concern_data["reasoning"],
                        related_questions=concern_data["related_questions"],
                        timestamp=datetime.now().isoformat()
                    )
                    new_concerns.append(concern)
                
                # Update state
                status = new_states.get(dimension)
                if status:
                    status.state = new_state
            
            return new_states, new_concerns
            
        except Exception as e:
            print(f"Error analyzing answer impact: {e}")
            raise
    
    async def check_completion(self, dimension_states: Dict[PrivacyDimension, DimensionStatus]) -> bool:
        """Check if analysis is complete (no potential issues remain)"""
        return all(
            status.state != DimensionState.POTENTIAL_ISSUE
            for status in dimension_states.values()
        )

# Main Privacy Analyzer
class PrivacyAnalyzer:
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)
        self.base_phase = BaseQuestionPhase(self.client)
        self.dimension_phase = DimensionAnalysisPhase(self.client)
        self.answer_generator = AnswerGenerator(self.client)

    async def analyze(self, design_purpose: str, data_practice: str) -> Dict:
        """Run complete privacy analysis"""
        try:
            # Phase 1: Base Questions
            print("\nPhase 1: Generating and processing base questions...")
            base_qa_pairs = await self.base_phase.process_base_phase(
                design_purpose,
                data_practice
            )
            print(f"Generated {len(base_qa_pairs)} base QA pairs")
            print("-" * 80)
            print("\nBase QA pairs:")
            for qa in base_qa_pairs:
                print(f"Q: {qa.question.text}\nA: {qa.answer.explanation}")
                print("-" * 80)
            # Initialize dimension states from base answers
            print("\nInitializing dimension states from base answers...")
            dimension_states = await self.dimension_phase.initialize_state(base_qa_pairs)
            qa_history = base_qa_pairs
            print(f"Initial states: {[f'{dim.value}: {status.state.value}' for dim, status in dimension_states.items()]}")
            # Phase 2: Dimension Analysis
            print("\nPhase 2: Starting dimension analysis...")
            question_count = len(base_qa_pairs)
            max_questions = 15  # Maximum total questions
            
            state_history = []
            
            while question_count < max_questions:
                # Check if analysis is complete
                if await self.dimension_phase.check_completion(dimension_states):
                    print("Analysis complete - no potential issues remain")
                    break

                # Generate follow-up question
                question = await self.dimension_phase.generate_follow_up_question(
                    dimension_states,
                    qa_history,
                    design_purpose,
                    data_practice
                )

                # Generate answer with dimension analysis
                answer = await self.answer_generator.generate_answer(data_practice, question)
                
                # Create QA pair
                qa_pair = QAPair(
                    question=question,
                    answer=answer,
                    timestamp=datetime.now().isoformat()
                )

                # Analyze impact and update states
                new_states, new_concerns = await self.dimension_phase.analyze_answer_impact(
                    qa_pair,
                    dimension_states
                )

                # Update tracking
                dimension_states = new_states
                qa_history.append(qa_pair)
                question_count += 1
                current_state =  {
                "states": {
                    dim.value: {
                        "state": status.state.value,
                        "concerns": [
                            {
                                "description": c.description,
                                "reasoning": c.reasoning,
                                "related_questions": c.related_questions
                            }
                            for c in status.concerns
                        ]
                    }
                    for dim, status in dimension_states.items()
                }
            }
                state_history.append({str(question_count):current_state.copy()})

                print(f"\nProcessed question {question_count}")
                print(f"Current states: {[f'{dim.value}: {status.state.value}' for dim, status in dimension_states.items()]}")

            #consturct the whole history of the states
            print("\nState History:")
            print(state_history)
   


            # Prepare results
            return {
                "qa_history": qa_history,
                "final_states": {
                    dim.value: {
                        "state": status.state.value,
                        "concerns": [
                            {
                                "description": c.description,
                                "reasoning": c.reasoning,
                                "related_questions": c.related_questions
                            }
                            for c in status.concerns
                        ]
                    }
                    for dim, status in dimension_states.items()
                },
                "state_history": state_history
             
            }

        except Exception as e:
            print(f"Error in privacy analysis: {e}")
            raise

    def save_results(self, case_name: str, results: Dict, output_dir: str = "results"):
        """Save analysis results to files"""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Save QA history
        qa_history_data = [
            {
                "question": {
                    "text": qa.question.text,
                    "options": qa.question.options,
                    "category": qa.question.category,
                    "related_dimensions": [d.value for d in qa.question.related_dimensions]
                },
                "answer": {
                    "selected_options": qa.answer.selected_options,
                    "explanation": qa.answer.explanation,
                    "impact_analysis": {
                        dim.value: impact
                        for dim, impact in qa.answer.impact_analysis.items()
                    }
                },
                "timestamp": qa.timestamp
            }
            for qa in results["qa_history"]
        ]
        
        with open(os.path.join(output_dir, f"{case_name}_[Agent].json"), 'w') as f:
            json.dump(qa_history_data, f, indent=2)

        # Save final states
        with open(os.path.join(output_dir, f"{case_name}_[Agent]_StateHistory.json"), 'w') as f:
            json.dump(results["state_history"], f, indent=2)

async def main():
    #load .env
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.getenv("api_key")
    if not api_key:
        raise ValueError("Please set OPENAI_API_KEY environment variable")

    # Load cases
    cases_df = pd.read_csv("privacy_cases.csv")
    
    # Initialize analyzer
    analyzer = PrivacyAnalyzer(api_key)
    
    # Process each case
    for _, case in cases_df.iterrows():
        try:
            print(f"\nProcessing case: {case['Case']}")
            results = await analyzer.analyze(
                case['Design Purpose'],
                case['Data Practice']
            )
            analyzer.save_results(case['Case'], results)
            print(f"Completed case: {case['Case']}")
        except Exception as e:
            print(f"Error processing case {case['Case']}: {e}")
            continue

    print("\nAll cases processed.")

if __name__ == "__main__":
    asyncio.run(main())