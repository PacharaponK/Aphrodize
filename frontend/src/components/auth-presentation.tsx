"use client";

import { createContext, useContext, useState, type Dispatch, type ReactNode, type SetStateAction } from "react";

type AuthStatus = "checking" | "signed-in" | "signed-out";
// Presentation only: API/session checks remain the authority for private data.
const AuthPresentation = createContext<{
  authStatus: AuthStatus;
  setAuthStatus: Dispatch<SetStateAction<AuthStatus>>;
}>({ authStatus: "checking", setAuthStatus: () => undefined });

export function AuthPresentationProvider({ children }: { children: ReactNode }) {
  const [authStatus, setAuthStatus] = useState<AuthStatus>("checking");
  return <AuthPresentation.Provider value={{ authStatus, setAuthStatus }}>{children}</AuthPresentation.Provider>;
}

export function useAuthPresentation() {
  return useContext(AuthPresentation);
}
