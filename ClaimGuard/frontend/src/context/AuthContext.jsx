import { createContext, useContext, useState, useEffect } from "react";
import { authAPI, usersAPI, saveToken, clearToken, getToken } from "../services/api";

const AuthContext = createContext(null);

// Role name normaliser – backend returns "Admin", "Provider", "Investigator"
function normaliseRole(raw) {
  if (!raw) return "provider";
  const s = raw.toLowerCase();
  if (s.includes("admin")) return "admin";
  if (s.includes("invest")) return "investigator";
  return "provider";
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true); // true during initial token check
  const [error, setError] = useState("");

  // ── On mount: restore session from stored token ──────────────────────────
  useEffect(() => {
    const token = getToken();
    if (token) {
      authAPI
        .getMe()
        .then((me) => {
          setUser({
            id: me.id,
            email: me.email,
            name: me.full_name,
            role: normaliseRole(me.role),
            roleId: me.role_id,
            avatar: me.full_name
              .split(" ")
              .map((w) => w[0])
              .join("")
              .toUpperCase()
              .slice(0, 2),
          });
        })
        .catch(() => {
          clearToken();
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  // ── Login ────────────────────────────────────────────────────────────────
  const login = async (email, password, remember = false) => {
    setLoading(true);
    setError("");
    try {
      const { access_token } = await authAPI.login(email, password);
      saveToken(access_token, remember);
      const me = await authAPI.getMe();
      const safeUser = {
        id: me.id,
        email: me.email,
        name: me.full_name,
        role: normaliseRole(me.role),
        roleId: me.role_id,
        avatar: me.full_name
          .split(" ")
          .map((w) => w[0])
          .join("")
          .toUpperCase()
          .slice(0, 2),
      };
      setUser(safeUser);
      setLoading(false);
      return { success: true, role: safeUser.role };
    } catch (err) {
      setError(err.message || "Invalid email or password.");
      setLoading(false);
      return { success: false };
    }
  };

  // ── Signup ───────────────────────────────────────────────────────────────
  const signup = async ({ name, email, password, role }) => {
    setLoading(true);
    setError("");
    try {
      await usersAPI.create({
        full_name: name,
        email,
        password,
        role, // backend resolves role_id from role string
      });
      setLoading(false);
      return { success: true };
    } catch (err) {
      setError(err.message || "Signup failed.");
      setLoading(false);
      return { success: false, error: err.message };
    }
  };

  // ── Logout ───────────────────────────────────────────────────────────────
  const logout = () => {
    setUser(null);
    clearToken();
  };

  return (
    <AuthContext.Provider
      value={{ user, login, logout, signup, loading, error, setError }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
