import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { ApiError, apiClient } from "@/controllers/apiClient";
import { useAuth } from "@/controllers/AuthContext";

export const RegisterPage: React.FC = () => {
  const navigate = useNavigate();
  const { registerWithEmail } = useAuth();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const errors: Record<string, string> = {};
    if (name.trim().length < 2) errors.name = "Name must be at least 2 characters.";
    if (!email.trim()) errors.email = "Please enter your email address.";
    if (password.length < 8) errors.password = "Password must be at least 8 characters.";

    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      return;
    }

    setIsSubmitting(true);
    setFieldErrors({});
    setGeneralError(null);
    try {
      await registerWithEmail(name.trim(), email.trim(), password);
      navigate("/", { replace: true });
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        if (err.fieldErrors && Object.keys(err.fieldErrors).length > 0) {
          setFieldErrors(err.fieldErrors);
        } else {
          setGeneralError(err.message);
        }
      } else {
        setGeneralError("Unable to create account. Please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F7F9FE] flex items-center justify-center p-6">
      <div className="w-full max-w-md bg-white border border-[#E5EBF5] rounded-3xl p-6 md:p-8 space-y-6 animate-page-enter">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-[#1264F5] text-white flex items-center justify-center font-bold text-lg">
            V
          </div>
          <div>
            <h1 className="text-base font-bold text-[#15213D] leading-tight">
              Create your Vocara account
            </h1>
            <p className="text-xs text-[#64748B] mt-0.5">
              Includes a Free Plan API key for voice synthesis
            </p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <label htmlFor="register-name" className="text-xs font-semibold text-[#15213D] block">
              Full Name
            </label>
            <input
              id="register-name"
              type="text"
              autoComplete="name"
              placeholder="Enter your name..."
              value={name}
              onChange={(e) => setName(e.target.value)}
              className={`w-full h-11 px-4 bg-white border rounded-xl text-sm text-[#15213D] placeholder:text-[#94A3B8] focus:outline-none focus:border-[#1264F5] ${
                fieldErrors.name ? "border-destructive" : "border-[#E5EBF5]"
              }`}
            />
            {fieldErrors.name && (
              <p className="text-xs text-destructive mt-1">{fieldErrors.name}</p>
            )}
          </div>

          <div className="space-y-1.5">
            <label htmlFor="register-email" className="text-xs font-semibold text-[#15213D] block">
              Email
            </label>
            <input
              id="register-email"
              type="email"
              autoComplete="email"
              placeholder="Enter your email..."
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className={`w-full h-11 px-4 bg-white border rounded-xl text-sm text-[#15213D] placeholder:text-[#94A3B8] focus:outline-none focus:border-[#1264F5] ${
                fieldErrors.email ? "border-destructive" : "border-[#E5EBF5]"
              }`}
            />
            {fieldErrors.email && (
              <p className="text-xs text-destructive mt-1">{fieldErrors.email}</p>
            )}
          </div>

          <div className="space-y-1.5">
            <label htmlFor="register-password" className="text-xs font-semibold text-[#15213D] block">
              Password
            </label>
            <input
              id="register-password"
              type="password"
              autoComplete="new-password"
              placeholder="Create a password (min 8 characters)..."
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={`w-full h-11 px-4 bg-white border rounded-xl text-sm text-[#15213D] placeholder:text-[#94A3B8] focus:outline-none focus:border-[#1264F5] ${
                fieldErrors.password ? "border-destructive" : "border-[#E5EBF5]"
              }`}
            />
            {fieldErrors.password && (
              <p className="text-xs text-destructive mt-1">{fieldErrors.password}</p>
            )}
          </div>

          {generalError && (
            <p className="text-xs text-destructive">{generalError}</p>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full h-11 rounded-full bg-[#1264F5] hover:bg-[#0E52CC] disabled:opacity-60 disabled:pointer-events-none text-white text-sm font-semibold flex items-center justify-center gap-2 transition-colors cursor-pointer"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Creating account...</span>
              </>
            ) : (
              <span>Create Free Account</span>
            )}
          </button>
        </form>

        <div className="relative flex items-center">
          <div className="flex-1 border-t border-[#E5EBF5]" />
          <span className="px-3 text-xs text-[#64748B]">or</span>
          <div className="flex-1 border-t border-[#E5EBF5]" />
        </div>

        <a
          href={apiClient.getGoogleLoginUrl()}
          className="w-full h-11 px-4 rounded-full border border-[#E5EBF5] bg-white hover:bg-[#F8FAFC] hover:border-[#CBD5E1] text-sm font-medium text-[#15213D] flex items-center justify-center gap-2.5 transition-colors"
        >
          <svg className="h-4 w-4" viewBox="0 0 24 24" aria-hidden="true">
            <path
              fill="#4285F4"
              d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.665-5.17 3.665-9.17Z"
            />
            <path
              fill="#34A853"
              d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.11-6.72-4.96H1.29v3.14C3.26 21.3 7.31 24 12 24Z"
            />
            <path
              fill="#FBBC05"
              d="M5.28 14.24c-.24-.72-.38-1.49-.38-2.24s.14-1.52.38-2.24V6.62H1.29C.47 8.24 0 10.06 0 12s.47 3.76 1.29 5.38l3.99-3.14Z"
            />
            <path
              fill="#EA4335"
              d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.31 0 3.26 2.7 1.29 6.62l3.99 3.14c.95-2.85 3.6-4.96 6.72-4.96Z"
            />
          </svg>
          <span>Continue with Google</span>
        </a>

        <p className="text-xs text-center text-[#64748B]">
          Already have an account?{" "}
          <Link to="/login" className="text-[#1264F5] font-semibold hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
};

