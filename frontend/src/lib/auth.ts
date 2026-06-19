export function getToken() {
  if (typeof window === "undefined") {
    return null;
  }

  const token = localStorage.getItem("access_token");

  if (
    !token ||
    token === "null" ||
    token === "undefined"
  ) {
    return null;
  }

  return token;
}


export function isAuthenticated() {
  return Boolean(getToken());
}


export function getUser() {
  if (typeof window === "undefined") {
    return null;
  }

  try {

    const user = localStorage.getItem("user");

    return user ? JSON.parse(user) : null;

  } catch {
    return null;
  }
}


export function clearAuth() {

  const user = getUser();

  if(user?.id){

    localStorage.removeItem(
      `serenity_conversations_${user.id}`
    );

    localStorage.removeItem(
      `serenity_active_${user.id}`
    );

  }


  localStorage.removeItem("access_token");
  localStorage.removeItem("user");


  window.dispatchEvent(
    new Event("auth-change")
  );
}