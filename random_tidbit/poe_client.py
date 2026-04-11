#! /usr/bin/env python3
#
# POE client written with the help of POE - Updated for OpenAI-compatible API
#
# Example usage:
#   client = POEClient(base_url="https://api.poe.com/v1", api_key="your_api_key")
#   response = client.ask(model="gpt-3.5-turbo", question="What is the capital of France?")
#   print(response)
#

"""
A Python client for interacting with POE (Platform for Open Exploration) LLMs via OpenAI-compatible API.
This module provides a class for basic Q&A functionality and extensibility for advanced features.

Sample usage:
    POE_API="..." {script} --command "What is the color of MAGA?"
"""

# Standard modules
import base64
import io
import re
from typing import Any, Dict, Optional, List

# Installed modules
import requests

# PIL/Pillow is optional — used for image format conversion on Android
# (Qt on p4a may lack JPEG/WebP plugins; PNG always works)
try:
    from PIL import Image as _PILImage
    _PIL_AVAILABLE = True
except ImportError:
    _PILImage = None
    _PIL_AVAILABLE = False

# Local modules
# TODO: def mezcla_import(name): ... components = eval(name).split(); ... import nameN-1.nameN as nameN
from mezcla import debug
from mezcla import glue_helpers as gh
from mezcla.main import Main
from mezcla import system


def _to_png_bytes(img_data: bytes) -> bytes:
    """Convert IMG_DATA to PNG format using PIL if available; otherwise return as-is.

    Qt on Android (p4a/PySide6) may lack JPEG/WebP image plugins, causing
    QPixmap.loadFromData() to fail.  PNG is always supported.  This function
    detects non-PNG input and re-encodes to PNG in-process so the caller can
    pass the result directly to loadFromData().
    """
    # PNG magic bytes: \x89PNG
    if img_data[:4] == b'\x89PNG':
        return img_data          # already PNG — no conversion needed
    if not _PIL_AVAILABLE:
        debug.trace(3, "_to_png_bytes: PIL not available; returning raw bytes as-is")
        return img_data
    try:
        buf = io.BytesIO(img_data)
        pil_img = _PILImage.open(buf)
        out = io.BytesIO()
        pil_img.save(out, format="PNG")
        png_data = out.getvalue()
        debug.trace(3, f"_to_png_bytes: converted {len(img_data)} bytes "
                    f"({pil_img.format}) → {len(png_data)} bytes PNG")
        return png_data
    except Exception:            # pylint: disable=broad-exception-caught
        system.print_exception_info("_to_png_bytes")
        return img_data


# Environment options
POE_API = system.getenv_value(
    "POE_API", None,
    desc="API key for POE")
# TODO: find out why POE_MODEL default was disabled (see git log)
POE_MODEL = system.getenv_value(
    ## OLD: "POE_MODEL", ("GPT-4.1-nano" if POE_API else None),
    "POE_MODEL", ("GPT-4.1-mini" if POE_API else None),
    desc="Default model for POE")
POE_URL = system.getenv_text(
    "POE_URL", "https://api.poe.com/v1",
    desc="Base URL for POE API")
POE_TIMEOUT = system.getenv_float(
    "POE_TIMEOUT", 30,
    desc="Timeout for POE API call")
POE_IMAGE_MODEL = system.getenv_text(
    "POE_IMAGE_MODEL", "FLUX-schnell",
    desc="Default model for POE image generation (e.g., FLUX-schnell, FLUX-pro)")
POE_IMAGE_SIZE = system.getenv_text(
    "POE_IMAGE_SIZE", "1024x1024",
    desc="Default image size for POE image generation")


class POEClient:
    """
    A Python client for interacting with POE LLMs via OpenAI-compatible API.
    Supports basic Q&A functionality and is designed to be extensible.
    """

    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None, timeout: Optional[float] = None, model: Optional[str] = None):
        """
        Initialize the client with the base URL of the POE API and an API key.

        Args:
            base_url (str): The base URL of the POE API.
            api_key (str): The API key for authentication.
            timeout (float): Timeout for HTTP requests in seconds (e.g., 30).
            model (str): Default model to use.
        """
        debug.trace_expr(6, base_url, api_key, timeout, model,
                         prefix="in __init__: ")
        if base_url is None:
            base_url = POE_URL
        self.base_url = base_url.rstrip("/")
        if api_key is None:
            api_key = POE_API
        self.api_key = api_key
        if timeout is None:
            timeout = POE_TIMEOUT
        self.timeout = timeout
        if model is None:
            ## OLD: debug.assertion(POE_MODEL)
            model = POE_MODEL
        self.model = model
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        debug.trace_object(5, self, label=f"{self.__class__.__name__} instance")

    def _send_request(
        self, endpoint: str, payload: Optional[Dict[str, Any]] = None, method: str = "POST"
    ) -> Dict[str, Any]:
        """
        Internal method to send a request to the POE API.

        Args:
            endpoint (str): The API endpoint (relative to the base URL).
            payload (Optional[Dict[str, Any]]): The request payload (optional).
            method (str): The HTTP method ("POST" or "GET").

        Returns:
            Dict[str, Any]: The API response as a dictionary.

        Raises:
            RuntimeError: If the request fails due to an HTTP or connection error.
        """
        debug.trace_expr(5, endpoint, payload, method,
                         prefix="in _send_request: ")
        
        url = f"{self.base_url}/{endpoint}"
        
        try:
            if method.upper() == "POST":
                response = requests.post(
                    url, headers=self.headers, json=payload, timeout=self.timeout
                )
            elif method.upper() == "GET":
                response = requests.get(
                    url, headers=self.headers, params=payload, timeout=self.timeout
                )
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            debug.trace_object(6, response)
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx and 5xx)
            
            result = response.json()
            debug.trace(5, f"_send_request() => {result}")
            return result
            
        except requests.exceptions.HTTPError as http_err:
            debug.raise_exception(6)
            error_details = ""
            try:
                error_response = http_err.response.json()
                error_details = f" - {error_response}"
            except:
                pass
            raise RuntimeError(
                f"HTTP error occurred: {http_err.response.status_code} {http_err.response.reason}{error_details}"
            ) from http_err
        except requests.exceptions.RequestException as req_err:
            debug.raise_exception(6)
            raise RuntimeError(f"Error in API request: {req_err}") from req_err

    def ask(self, question: str, model: Optional[str] = None, context: Optional[str] = None, 
            temperature: float = 0.7, max_tokens: Optional[int] = None) -> str:
        """
        Send a question to the specified model with optional context using OpenAI chat completions format.

        Args:
            question (str): The question to ask the model.
            model (Optional[str]): The name of the model to use (uses default if None).
            context (Optional[str]): Additional context for the model (optional).
            temperature (float): Controls randomness in the response (0.0 to 2.0).
            max_tokens (Optional[int]): Maximum number of tokens in the response.

        Returns:
            str: The model's response.
        """
        debug.trace_expr(6, model, question, context, temperature, max_tokens,
                         prefix="in ask: ")
        
        if model is None:
            model = self.model
            
        messages = []
        if context:
            messages.append({"role": "system", "content": context})
        messages.append({"role": "user", "content": question})
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        response = self._send_request("chat/completions", payload)
        
        # Extract the response content from OpenAI format
        try:
            result = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            debug.trace(4, f"Unexpected response format:\n\t{response}\n\t{e}")
            result = response.get("output", str(response))
        debug.trace(5, f"ask() => {result}")
        return result

    def create_chat_completion(self, messages: List[Dict[str, str]], model: Optional[str] = None,
                              temperature: float = 0.7, max_tokens: Optional[int] = None,
                              stream: bool = False, **kwargs) -> Dict[str, Any]:
        """
        Create a chat completion using the OpenAI chat completions format.

        Args:
            messages (List[Dict[str, str]]): List of messages in OpenAI format.
            model (Optional[str]): The name of the model to use.
            temperature (float): Controls randomness in the response.
            max_tokens (Optional[int]): Maximum number of tokens in the response.
            stream (bool): Whether to stream the response (not yet implemented).
            **kwargs: Additional parameters to pass to the API.

        Returns:
            Dict[str, Any]: The complete API response.
        """
        debug.trace_expr(6, messages, model, temperature, max_tokens, stream,
                         prefix="in create_chat_completion: ")
        
        if model is None:
            model = self.model
            
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            **kwargs
        }
        
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
            
        if stream:
            payload["stream"] = stream
            # TODO: Implement streaming support
            debug.trace(3, "Warning: Streaming not yet implemented")

        result = self._send_request("chat/completions", payload)
        debug.trace(5, f"create_chat_completion() => {result}")
        return result

    def list_models(self) -> Dict[str, Any]:
        """
        List available models.

        Returns:
            Dict[str, Any]: The list of available models.
        """
        debug.trace(5, "in list_models")
        return self._send_request("models", method="GET")

    def call_function(self, function_name: str, arguments: Dict[str, Any], 
                     model: Optional[str] = None, context: Optional[str] = None) -> Any:
        """
        Call a specific function using function calling in chat completions.

        Args:
            function_name (str): The name of the function to call.
            arguments (Dict[str, Any]): The arguments for the function.
            model (Optional[str]): The name of the model to use.
            context (Optional[str]): Additional context for the function call.

        Returns:
            Any: The function's output.
        """
        debug.trace_expr(6, model, function_name, arguments, context,
                         prefix="in call_function: ")
        
        if model is None:
            model = self.model

        messages = []
        if context:
            messages.append({"role": "system", "content": context})
        messages.append({
            "role": "user", 
            "content": f"Please call the function {function_name} with these arguments: {arguments}"
        })

        # Define the function for function calling
        functions = [{
            "name": function_name,
            "description": f"Call the {function_name} function",
            "parameters": {
                "type": "object",
                "properties": {key: {"type": "string"} for key in arguments.keys()},
                "required": list(arguments.keys())
            }
        }]

        payload = {
            "model": model,
            "messages": messages,
            "functions": functions,
            "function_call": {"name": function_name}
        }

        response = self._send_request("chat/completions", payload)
        
        try:
            function_call = response["choices"][0]["message"].get("function_call")
            if function_call:
                response = function_call.get("arguments", {})
            else:
                response = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            response = response.get("output")
        
        debug.trace(5, f"call_function() => {response}")
        return response

    def extend(self, extension_name: str, params: Dict[str, Any], model: Optional[str] = None) -> Dict[str, Any]:
        """
        Extend the model's capabilities using chat completions with custom instructions.

        Args:
            extension_name (str): The name of the extension to apply.
            params (Dict[str, Any]): Parameters for the extension.
            model (Optional[str]): The name of the model to use.

        Returns:
            Dict[str, Any]: The extension's result.
        """
        debug.trace_expr(5, model, extension_name, params,
                         prefix="in extend: ")
        
        if model is None:
            model = self.model

        # Convert extension call to a chat completion
        system_message = f"You are operating in {extension_name} mode with the following parameters: {params}"
        user_message = f"Please process this request using the {extension_name} extension."

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ]

        response = self.create_chat_completion(messages, model=model)
        debug.trace(5, f"extend() => {response}")
        return response


    def generate_image_prompt(self, tidbit: str, model: Optional[str] = None,
                              age_group: Optional[str] = None) -> str:
        """
        Convert a text tidbit into a visual image generation prompt via an LLM call.
        Emphasizes concrete visual terms and applies NSFW-style filtering.

        Args:
            tidbit (str): The historical tidbit text to convert.
            model (Optional[str]): The LLM model to use for prompt conversion.
            age_group (Optional[str]): Target audience age group (e.g., "3-5", "18+").

        Returns:
            str: A safe, visually descriptive image generation prompt.
        """
        debug.trace_expr(6, tidbit, model, age_group, prefix="in generate_image_prompt: ")
        if age_group and age_group != "18+":
            age_clause = (
                f"The image must be strictly appropriate for ages {age_group}: "
                "no violence, no romance, no adult themes, only child-friendly imagery. "
            )
        else:
            age_clause = ""
        context = (
            "You are a visual prompt specialist for image generation. "
            "Convert the given historical tidbit into a concise image generation prompt "
            "(under 100 words) that emphasizes concrete visual elements: setting, objects, "
            "clothing, colors, lighting, and artistic style. "
            f"{age_clause}"
            "The result must be safe for work and family-friendly. "
            "Strictly avoid any adult content, graphic violence, disturbing imagery, or NSFW material. "
            "Output only the prompt text, with no preamble or explanation."
        )
        result = self.ask(
            question=f"Convert this historical tidbit into a visual image prompt:\n\n{tidbit}",
            model=model,
            context=context,
            temperature=0.5,
            max_tokens=120,
        )
        debug.trace(5, f"generate_image_prompt() => {result!r}")
        return result

    def generate_image(self, prompt: str, model: Optional[str] = None,
                       size: Optional[str] = None, n: int = 1) -> Optional[bytes]:
        """
        Generate an image using POE's image generation API.

        Args:
            prompt (str): The image generation prompt.
            model (Optional[str]): The image model to use (defaults to POE_IMAGE_MODEL).
            size (Optional[str]): Image dimensions, e.g. "1024x1024".
            n (int): Number of images to generate.

        Returns:
            Optional[bytes]: Raw image bytes, or None on failure.
        """
        debug.trace_expr(5, prompt, model, size, n, prefix="in generate_image: ")
        if model is None:
            model = POE_IMAGE_MODEL
        if size is None:
            size = POE_IMAGE_SIZE

        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "n": n,
            "size": size,
        }

        image_bytes = None
        try:
            response = self._send_request("images/generations", payload)
            debug.trace(6, f"generate_image raw response: {response}")
            data_list = response.get("data", [])
            if not data_list:
                debug.trace(3, "generate_image: empty data list in response")
            else:
                item = data_list[0]
                # Support both URL-based and base64-encoded responses
                if "url" in item:
                    img_url = item["url"]
                    debug.trace(5, f"generate_image: downloading from {img_url}")
                    img_response = requests.get(img_url, timeout=self.timeout)
                    img_response.raise_for_status()
                    image_bytes = img_response.content
                elif "b64_json" in item:
                    image_bytes = base64.b64decode(item["b64_json"])
                else:
                    debug.trace(3, f"generate_image: unrecognized item format: {item}")
        except Exception:             # pylint: disable=broad-exception-caught
            system.print_exception_info("generate_image")
        # Fallback: try accessing the image model via the chat completions endpoint.
        # POE image bots (e.g. FLUX-schnell) are callable this way even when the
        # dedicated /images/generations endpoint is not enabled for the account.
        if not image_bytes:
            debug.trace(3, "generate_image: /images/generations unavailable; trying chat fallback")
            image_bytes = self._generate_image_via_chat(prompt, model=model)
        debug.trace(5, f"generate_image() => {len(image_bytes) if image_bytes else 0} bytes")
        return image_bytes

    def _generate_image_via_chat(self, prompt: str, model: Optional[str] = None) -> Optional[bytes]:
        """Call an image-generation model through the chat completions endpoint.
        POE image bots return the generated image as a URL or base64 data embedded in
        the assistant message content (often as markdown `![](url)` or a bare URL).
        MODEL: image generation model name (defaults to POE_IMAGE_MODEL).
        """
        if model is None:
            model = POE_IMAGE_MODEL
        debug.trace(5, f"_generate_image_via_chat: model={model!r} prompt={prompt!r}")
        try:
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
            }
            response = self._send_request("chat/completions", payload)
            choices = response.get("choices", [])
            if not choices:
                debug.trace(3, "_generate_image_via_chat: no choices in response")
                return None
            content = choices[0].get("message", {}).get("content", "")
            debug.trace(5, f"_generate_image_via_chat: content={content!r}")
            # Try markdown image syntax: ![alt](url)
            match = re.search(r'!\[.*?\]\((https?://\S+?)\)', content)
            if not match:
                # Try bare image URL
                match = re.search(
                    r'(https?://\S+\.(?:png|jpg|jpeg|webp|gif)\S*)',
                    content, re.IGNORECASE)
            if match:
                img_url = match.group(1).rstrip(")")
                debug.trace(4, f"_generate_image_via_chat: downloading {img_url}")
                dl = requests.get(img_url, timeout=self.timeout)
                dl.raise_for_status()
                content_type = dl.headers.get("content-type", "unknown")
                img_data = dl.content
                debug.trace(3, f"_generate_image_via_chat: downloaded {len(img_data)} bytes "
                            f"content-type={content_type!r} magic={img_data[:8]!r}")
                img_data = _to_png_bytes(img_data)
                return img_data
            # Try inline base64
            b64_match = re.search(r'data:image/\w+;base64,([A-Za-z0-9+/=]+)', content)
            if b64_match:
                return base64.b64decode(b64_match.group(1))
            debug.trace(3, "_generate_image_via_chat: no image found in response content")
        except Exception:             # pylint: disable=broad-exception-caught
            system.print_exception_info("_generate_image_via_chat")
        return None


def main():
    """Entry point for testing"""
    debug.trace(4, "POE Client - OpenAI Compatible API")
    
    # Parse command line options, show usage if --help given
    LIST_MODELS_ARG = "list-models"
    COMMAND_ARG = "command"
    STDIO_ARG = "stdio"
    main_app = Main(
        description=__doc__.format(script=gh.basename(__file__)),
        boolean_options=[(LIST_MODELS_ARG, "List available LLM models"),
                         (STDIO_ARG, "Use stdin for command (and plain stdout for output)")],
        text_options=[(COMMAND_ARG, "Command or question for LLM")],
    )
    debug.assertion(main_app.parsed_args)
    list_models = main_app.get_parsed_option(LIST_MODELS_ARG)
    llm_command = main_app.get_parsed_option(COMMAND_ARG)
    use_stdio = main_app.get_parsed_option(STDIO_ARG)
    if use_stdio:
        debug.assertion(not llm_command)
        llm_command = main_app.read_entire_input()
    
    # Example usage
    if not POE_API:
        system.exit("Error: POE_API environment variable not set. Cannot run client.")
    try:
        client = POEClient()
        
        # Test model listing
        if list_models:
            models = client.list_models()
            print(f"Available models:\n\t{models}")
            
        # Test basic ask functionality
        if llm_command:
            response = client.ask(llm_command)
            print(f"Response:\n\t{response}" if not use_stdio else response)
        
    except:
        system.print_exception_info("Error testing client")

#-------------------------------------------------------------------------------

if __name__ == '__main__':
    debug.trace_current_context(6)
    debug.trace(5, f"module __doc__: {__doc__}")
    main()
