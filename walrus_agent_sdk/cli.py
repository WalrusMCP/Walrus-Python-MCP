"""
Command-line interface for Walrus Agent SDK.

Provides scaffolding and code generation tools to quickly set up
blockchain-connected AI agents.
"""
import os
import sys
import json
import logging
import shutil
import click
from typing import Dict, List, Any, Optional
from pathlib import Path

from walrus_agent_sdk.storage import StorageGranularity
from walrus_agent_sdk.blockchain import EventType
from walrus_agent_sdk.utils import ensure_directory

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Template paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "examples")

# Templates
TEMPLATES = {
    "nft_customer_service": {
        "description": "NFT Customer Service Bot",
        "files": [
            "nft_customer_service.py",
            os.path.join("templates", "nft_customer_service.html"),
            os.path.join("templates", "base.html")
        ]
    },
    "rwa_data_oracle": {
        "description": "Real-World Asset Data Oracle",
        "files": [
            "rwa_data_oracle.py",
        ]
    },
    "auto_market_maker": {
        "description": "Automatic Market Making Bot",
        "files": [
            "auto_market_maker.py",
        ]
    }
}

@click.group()
def cli():
    """Walrus Agent MCP SDK - CLI tools for blockchain-connected AI agents."""
    pass

@cli.command()
@click.option('--agent-name', '-n', required=True, help='Name of the agent to create')
@click.option('--template', '-t', type=click.Choice(list(TEMPLATES.keys())), 
              required=True, help='Template to use for the agent')
@click.option('--output-dir', '-o', default='.', help='Output directory for the agent')
@click.option('--force', '-f', is_flag=True, help='Overwrite existing files')
def create(agent_name: str, template: str, output_dir: str, force: bool):
    """Create a new agent from a template."""
    try:
        # Create output directory
        agent_dir = os.path.join(output_dir, agent_name)
        ensure_directory(agent_dir)
        
        # Ensure template directories exist
        ensure_directory(os.path.join(agent_dir, "templates"))
        
        # Copy template files
        template_info = TEMPLATES[template]
        for file_path in template_info["files"]:
            source_path = os.path.join(TEMPLATE_DIR, file_path)
            dest_path = os.path.join(agent_dir, file_path)
            
            # Create directories if they don't exist
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            
            # Check if destination file exists
            if os.path.exists(dest_path) and not force:
                click.echo(f"Error: File {dest_path} already exists. Use --force to overwrite.")
                return
            
            # Copy the file
            shutil.copy2(source_path, dest_path)
            
            # Replace template variables in the file
            with open(dest_path, 'r') as f:
                content = f.read()
            
            content = content.replace('__AGENT_NAME__', agent_name)
            
            with open(dest_path, 'w') as f:
                f.write(content)
        
        # Create agent configuration file
        config = {
            "agent_name": agent_name,
            "template": template,
            "storage_granularity": StorageGranularity.FULL_CONVERSATION.value,
            "model_name": "gpt-3.5-turbo",
            "created_at": os.path.getmtime(agent_dir)
        }
        
        with open(os.path.join(agent_dir, "agent_config.json"), 'w') as f:
            json.dump(config, f, indent=2)
        
        click.echo(f"Successfully created agent '{agent_name}' from template '{template}'")
        click.echo(f"Agent files are located in: {agent_dir}")
        click.echo("To run the agent, navigate to the agent directory and run:")
        click.echo(f"  python {os.path.basename(TEMPLATES[template]['files'][0])}")
        
    except Exception as e:
        logger.error(f"Error creating agent: {e}")
        click.echo(f"Error: {e}")

@cli.command()
@click.option('--agent-name', '-n', required=True, help='Name of the agent to generate code for')
@click.option('--event-name', '-e', required=True, help='Name of the event to handle')
@click.option('--output-file', '-o', required=True, help='Output file for the generated code')
@click.option('--force', '-f', is_flag=True, help='Overwrite existing file')
def generate_handler(agent_name: str, event_name: str, output_file: str, force: bool):
    """Generate code for an event handler."""
    try:
        # Check if output file exists
        if os.path.exists(output_file) and not force:
            click.echo(f"Error: File {output_file} already exists. Use --force to overwrite.")
            return
        
        # Normalize event name
        event_name_normalized = event_name.lower().replace(' ', '_')
        
        # Try to match with a known event type
        try:
            event_type = EventType[event_name.upper()]
            event_type_str = f"EventType.{event_type.name}"
        except KeyError:
            event_type_str = "EventType.CUSTOM"
        
        # Generate the code
        code = f"""# Generated code for {agent_name} to handle {event_name} events

from walrus_agent_sdk import WalrusAgent, StorageGranularity
from walrus_agent_sdk.blockchain import EventType

# Initialize the agent
agent = WalrusAgent(
    agent_name="{agent_name}",
    storage_granularity=StorageGranularity.FULL_CONVERSATION
)

# Define the event handler
@agent.on_event("{event_name_normalized}")
def handle_{event_name_normalized}(event_data):
    \"\"\"Handle {event_name} events.\"\"\"
    
    # Process the event with AI/LLM
    prompt = f\"\"\"
    I received a {event_name} event from the blockchain. Here are the details:
    {{event_data}}
    
    Please analyze this event and provide a helpful response.
    \"\"\"
    
    response = agent.process(prompt, event_data)
    
    # Log the response
    print(f"Processed {event_name} event. Response: {{response['response']}}")
    
    # Return the response
    return response

# Examples of how to trigger or test this handler
if __name__ == "__main__":
    # For testing, you can create a mock event
    mock_event = {{
        "type": "{event_name_normalized}",
        "timestamp": 1234567890,
        "data": {{
            "field1": "value1",
            "field2": "value2"
        }}
    }}
    
    # Test the handler with the mock event
    handle_{event_name_normalized}(mock_event)
"""
        
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
        
        # Write the code to the output file
        with open(output_file, 'w') as f:
            f.write(code)
        
        click.echo(f"Successfully generated handler for '{event_name}' events")
        click.echo(f"Handler code written to: {output_file}")
        
    except Exception as e:
        logger.error(f"Error generating handler: {e}")
        click.echo(f"Error: {e}")

@cli.command()
def list_templates():
    """List available templates."""
    click.echo("Available templates:")
    for name, info in TEMPLATES.items():
        click.echo(f"  {name}: {info['description']}")

@cli.command()
@click.option('--storage-dir', '-s', default='.walrus_storage', help='Storage directory to inspect')
def inspect_storage(storage_dir: str):
    """Inspect the agent storage directory."""
    try:
        if not os.path.exists(storage_dir):
            click.echo(f"Storage directory {storage_dir} does not exist.")
            return
        
        # List agent directories
        agent_dirs = [d for d in os.listdir(storage_dir) 
                     if os.path.isdir(os.path.join(storage_dir, d))]
        
        if not agent_dirs:
            click.echo(f"No agents found in storage directory {storage_dir}.")
            return
        
        click.echo(f"Found {len(agent_dirs)} agent(s) in storage directory {storage_dir}:")
        
        for agent_dir in agent_dirs:
            agent_path = os.path.join(storage_dir, agent_dir)
            
            # Check storage type based on directory contents
            storage_type = "Unknown"
            if any(f.endswith('.json') for f in os.listdir(agent_path)):
                # Check for version directories
                has_version_dirs = any(os.path.isdir(os.path.join(agent_path, d)) 
                                     for d in os.listdir(agent_path))
                
                if has_version_dirs:
                    storage_type = "Historical Versions"
                else:
                    # Examine a sample file to determine type
                    sample_file = next((f for f in os.listdir(agent_path) if f.endswith('.json')), None)
                    if sample_file:
                        try:
                            with open(os.path.join(agent_path, sample_file), 'r') as f:
                                data = json.load(f)
                                if "messages" in data:
                                    storage_type = "Full Conversation"
                                elif "summary" in data:
                                    storage_type = "Summary Only"
                        except:
                            pass
            
            # Count contexts
            context_count = 0
            if storage_type == "Historical Versions":
                context_count = sum(1 for d in os.listdir(agent_path) 
                                  if os.path.isdir(os.path.join(agent_path, d)))
            else:
                context_count = sum(1 for f in os.listdir(agent_path) 
                                  if f.endswith('.json'))
            
            click.echo(f"  Agent: {agent_dir}")
            click.echo(f"    Storage Type: {storage_type}")
            click.echo(f"    Contexts: {context_count}")
        
    except Exception as e:
        logger.error(f"Error inspecting storage: {e}")
        click.echo(f"Error: {e}")

if __name__ == '__main__':
    cli()
