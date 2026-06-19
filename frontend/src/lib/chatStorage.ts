import type { Conversation } from "@/routes/chat";


const CHAT_PREFIX = "serenity_chats_";


export function getCurrentUserId(){

  const user = JSON.parse(
    localStorage.getItem("user") || "null"
  );

  return user?.id ?? null;
}



function getKey(){

  const id = getCurrentUserId();

  if(!id) return null;

  return `${CHAT_PREFIX}${id}`;

}



export function loadChats(){

  try {

    const key = getKey();

    if(!key) return [];

    const data = localStorage.getItem(key);

    return data ? JSON.parse(data) : [];

  } catch {

    return [];

  }

}



export function saveChats(chats:any[]){

  const key = getKey();

  if(!key) return;


  localStorage.setItem(
    key,
    JSON.stringify(chats)
  );

}



export function clearUserChats(){

  const id = getCurrentUserId();

  if(!id) return;


  localStorage.removeItem(
    `${CHAT_PREFIX}${id}`
  );

  localStorage.removeItem(
    `serenity_active_${id}`
  );

}