// Cloudflare Pages Function: POST /api/chat. Set OPENAI_API_KEY as a secret in the Pages project.
import { handleChat } from "../../server/tutor.js";

export const onRequest = ({ request, env }) => handleChat(request, env);
