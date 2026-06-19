import { apiClient } from "./client";


export interface ChatMessage {
    message:string;
}


export interface ChatResponse {
    response:string;
}



export function sendMessage(
    data:ChatMessage
){

 return apiClient<ChatResponse>(
   "/chat",
   {
    method:"POST",
    body:JSON.stringify(data)
   }
 );

}