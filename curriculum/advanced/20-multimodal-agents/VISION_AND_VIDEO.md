# Deep Dive: Vision, Video, and Structured Extraction

Multimodal perception allows an agent to process PDFs, images, and videos. But passing a raw image to an LLM and asking "What do you see?" is usually useless for an autonomous agent. Agents need structured data.

## 1. Structured Vision Extraction

When an agent processes an image (e.g., a scanned PDF receipt), you should not ask for a prose summary. You must force the vision model to return strict JSON matching a schema (e.g., using `response_format={"type": "json_schema"}` in OpenAI).

**The Hallucination Risk:** Vision models are notorious for hallucinating text that looks blurry. If a receipt says "$10.00" but it is smudged, the model might extract "$100.00".
**Mitigation:** You must implement a deterministic validation layer. If the extracted JSON says the items cost $5 + $5, but the extracted total is $100, your code must reject the payload before the agent is allowed to act on it.

## 2. Token Economics of Media

Passing an image to an LLM is not free. A high-resolution 1080p image can cost thousands of tokens.
- **Low-Res vs High-Res:** Only use "high detail" mode if you need OCR (Optical Character Recognition) on small text. If you just need to know if a door is open or closed, downsample the image to 512x512 and use "low detail" mode to save 90% of the cost.

## 3. Video Processing (Frame Extraction vs Native Multimodal)

There are two ways to process a 10-minute video:
1. **Frame Extraction (The Old Way):** You write an FFMPEG script to extract 1 frame per second, generating 600 images. You send all 600 images to the LLM. This is incredibly expensive and loses audio context.
2. **Native Multimodal (The Modern Way):** Models like Gemini 1.5 Pro allow you to upload the raw `.mp4` file directly into the context window. The model natively processes the audio, the frames, and the timestamps, allowing you to ask: *"At what timestamp does the user mention the error code?"*
