import { apiClient } from "./client";
import { getToken } from "@/lib/auth";


export async function sendVoice(
  audio: Blob
) {

  const formData = new FormData();


  formData.append(
    "audio",
    audio,
    "voice.webm"
  );


  const token = getToken();


  const response = await fetch(
    `${import.meta.env.VITE_API_URL}/voice`,
    {
      method: "POST",

      headers: {
        Authorization: `Bearer ${token}`,
      },

      body: formData,
    }
  );


  if(!response.ok){

    const error = await response.json();

    throw new Error(
      error.detail || "Voice request failed"
    );

  }


  return response.json();

}