import { register } from "@/lib/api/auth.functions";
import { useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { Eye, EyeOff, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";
import serenityIcon from "@/assets/serenity-logo-only.png";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import authBloom from "@/assets/auth-bloom.png";
import Select from "react-select";
import countryList from "react-select-country-list";
import ReactCountryFlag from "react-country-flag";
import { useMemo } from "react";
import { useNavigate } from "@tanstack/react-router";

export const Route = createFileRoute("/register")({
  head: () => ({
    meta: [
      { title: "Create Account — Serenity" },
      { name: "description", content: "Join Serenity and start your personalized journey toward emotional wellness and growth." },
    ],
  }),
  component: RegisterPage,
});

type FormState = {
  firstName: string;
  lastName: string;
  username: string;
  email: string;
  country: string;
  password: string;
  confirmPassword: string;
};

type FormErrors = Partial<Record<keyof FormState, string>>;

type SubmitStatus =
  | { type: "success"; message: string }
  | { type: "error"; message: string }
  | null;

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const USERNAME_REGEX = /^[a-zA-Z0-9_]+$/;

function validate(form: FormState): FormErrors {
  const errors: FormErrors = {};

  if (!form.firstName.trim()) errors.firstName = "First name is required.";
  if (!form.lastName.trim()) errors.lastName = "Last name is required.";

  if (!form.username.trim()) {
    errors.username = "Username is required.";
  } else if (form.username.length < 3) {
    errors.username = "Username must be at least 3 characters.";
  } else if (!USERNAME_REGEX.test(form.username)) {
    errors.username = "Username can only contain letters, numbers, and underscores.";
  }

  if (!form.email.trim()) {
    errors.email = "Email is required.";
  } else if (!EMAIL_REGEX.test(form.email)) {
    errors.email = "Please enter a valid email address.";
  }

  if (!form.country.trim()) errors.country = "Country is required.";

  if (!form.password) {
    errors.password = "Password is required.";
  } else if (form.password.length < 8) {
    errors.password = "Password must be at least 8 characters.";
  }

  if (!form.confirmPassword) {
    errors.confirmPassword = "Please confirm your password.";
  } else if (form.password !== form.confirmPassword) {
    errors.confirmPassword = "Passwords do not match.";
  }

  return errors;
}

function RegisterPage() {
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [status, setStatus] = useState<SubmitStatus>(null);
  const [errors, setErrors] = useState<FormErrors>({});
  const navigate = useNavigate();
  const [form, setForm] = useState<FormState>({
    firstName: "",
    lastName: "",
    username: "",
    email: "",
    country: "",
    password: "",
    confirmPassword: "",
  });
  
  const countries = useMemo(
  () =>
    countryList().getData().map((country) => ({
      value: country.value,
      label: country.label,
    })),
  []
);

  const update = (field: keyof FormState) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm((prev) => ({ ...prev, [field]: e.target.value }));
    // Clear that field's error as soon as the user starts correcting it
    setErrors((prev) => {
      if (!prev[field]) return prev;
      const next = { ...prev };
      delete next[field];
      return next;
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
  e.preventDefault();
  setStatus(null);

  const validationErrors = validate(form);
  setErrors(validationErrors);

  if (Object.keys(validationErrors).length > 0) {
    setStatus({
      type: "error",
      message: "Please fix the errors below and try again.",
    });
    return;
  }

  setIsSubmitting(true);

  try {

    const response = await register({
      username: form.username,
      email: form.email,
      password: form.password,

      country: form.country,
      first_name: form.firstName,
      last_name: form.lastName,
    });


    setStatus({
      type: "success",
      message:
        `Welcome, ${form.firstName}! Your account has been created successfully.`,
    });


    console.log("Register response:", response);


    // optional:
    // navigate to login page after success
    // router.navigate({to:"/login"})
    setTimeout(() => {
      navigate({
        to: "/login",
        replace: true,
      });
    }, 1500);


  } catch (error) {

    console.error(error);

    setStatus({
      type:"error",
      message:
        error instanceof Error
        ? error.message
        : "Registration failed. Please try again."
    });

  } finally {

    setIsSubmitting(false);

  }
};

  return (
    <div className="flex min-h-dvh w-full">
      {/* Left side — illustration + quote */}
      <div className="relative hidden w-[45%] flex-col items-center justify-center overflow-hidden bg-gradient-petal lg:flex">
        <div className="absolute inset-0 bg-gradient-sunlight" />
        <div className="relative z-10 flex flex-col items-center px-12 text-center">
          <img
            src={authBloom}
            alt="Blooming flower emerging from seed illustration"
            width={380}
            height={380}
            className="mb-8 drop-shadow-xl animate-bloom-in"
            loading="eager"
          />
          <blockquote className="max-w-sm">
            <p className="font-display text-2xl font-semibold leading-relaxed text-violet-deep">
              “Every beautiful bloom was once a tiny seed brave enough to trust the soil.”
            </p>
          </blockquote>
          <div className="mt-6 flex items-center gap-1 text-sm text-foreground/60">
            <Link to="/" className="flex items-center gap-1 transition-opacity hover:opacity-80">
              <img
                src={serenityIcon}
                alt=""
                className="h-18 w-18 object-contain"
              />
              <span className="-ml-3">Serenity</span>
            </Link>
          </div>
        </div>
        {/* Decorative floating petals */}
        <div className="absolute bottom-10 left-10 h-16 w-16 rounded-full bg-sunflower/20 blur-2xl animate-float-leaf" />
        <div className="absolute top-20 right-16 h-12 w-12 rounded-full bg-lavender/30 blur-2xl animate-sway" />
      </div>

      {/* Right side — form */}
      <div className="flex flex-1 flex-col items-center justify-center px-6 py-12 sm:px-12 lg:px-20">
        <div className="w-full max-w-md">
          {/* Mobile logo */}
          <Link
            to="/"
            className="mt-6 flex items-center gap-1 text-sm text-foreground/60 transition-opacity hover:opacity-80"
          >
            <img
              src={serenityIcon}
              alt=""
              className="h-18 w-18 object-contain"
            />
            <span className="-ml-3">Serenity</span>
          </Link>

          <h1 className="mt-6 font-display text-3xl font-bold tracking-tight text-foreground">
            Create your account
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Start your journey toward growth and emotional wellness.
          </p>

          {/* Success / error status box */}
          {status && (
            <div
              role="alert"
              className={`mt-6 flex items-start gap-3 rounded-xl border px-4 py-3 text-sm ${
                status.type === "success"
                  ? "border-green-200 bg-green-50 text-green-800"
                  : "border-destructive/30 bg-destructive/10 text-destructive"
              }`}
            >
              {status.type === "success" ? (
                <CheckCircle2 className="mt-0.5 h-5 w-5 flex-shrink-0" />
              ) : (
                <AlertCircle className="mt-0.5 h-5 w-5 flex-shrink-0" />
              )}
              <p>{status.message}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="mt-8 space-y-5" noValidate>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="firstName">First Name</Label>
                <Input
                  id="firstName"
                  placeholder="Jane"
                  value={form.firstName}
                  onChange={update("firstName")}
                  aria-invalid={!!errors.firstName}
                  className={`h-11 rounded-xl ${errors.firstName ? "border-destructive focus-visible:ring-destructive" : ""}`}
                />
                {errors.firstName && <p className="text-xs text-destructive">{errors.firstName}</p>}
              </div>
              <div className="space-y-2">
                <Label htmlFor="lastName">Last Name</Label>
                <Input
                  id="lastName"
                  placeholder="Doe"
                  value={form.lastName}
                  onChange={update("lastName")}
                  aria-invalid={!!errors.lastName}
                  className={`h-11 rounded-xl ${errors.lastName ? "border-destructive focus-visible:ring-destructive" : ""}`}
                />
                {errors.lastName && <p className="text-xs text-destructive">{errors.lastName}</p>}
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="username">Username</Label>
              <Input
                id="username"
                placeholder="jane_doe"
                value={form.username}
                onChange={update("username")}
                aria-invalid={!!errors.username}
                className={`h-11 rounded-xl ${errors.username ? "border-destructive focus-visible:ring-destructive" : ""}`}
              />
              {errors.username && <p className="text-xs text-destructive">{errors.username}</p>}
            </div>

            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="you@example.com"
                value={form.email}
                onChange={update("email")}
                aria-invalid={!!errors.email}
                className={`h-11 rounded-xl ${errors.email ? "border-destructive focus-visible:ring-destructive" : ""}`}
              />
              {errors.email && <p className="text-xs text-destructive">{errors.email}</p>}
            </div>

            <div className="space-y-2">
              <Label htmlFor="country">Country</Label>

              <Select
                options={countries}
                isSearchable
                placeholder="Select your country"
                value={
                  countries.find(
                    (country) => country.label === form.country
                  ) || null
                }
                onChange={(selected) => {
                  setForm((prev) => ({
                    ...prev,
                    country: selected?.label || "",
                  }));

                  setErrors((prev) => {
                    if (!prev.country) return prev;
                    const next = { ...prev };
                    delete next.country;
                    return next;
                  });
                }}
                formatOptionLabel={(country) => (
                  <div className="flex items-center gap-3">
                    <ReactCountryFlag
                      countryCode={country.value}
                      svg
                      style={{
                        width: "1.4em",
                        height: "1.4em",
                      }}
                    />
                    <span>{country.label}</span>
                  </div>
                )}
                className="text-sm"
                styles={{
                  control: (base) => ({
                    ...base,
                    minHeight: "44px",
                    borderRadius: "12px",
                  }),
                }}
              />

              {errors.country && (
                <p className="text-xs text-destructive">
                  {errors.country}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  placeholder="Create a strong password"
                  value={form.password}
                  onChange={update("password")}
                  aria-invalid={!!errors.password}
                  className={`h-11 rounded-xl pr-10 ${errors.password ? "border-destructive focus-visible:ring-destructive" : ""}`}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              {errors.password && <p className="text-xs text-destructive">{errors.password}</p>}
            </div>

            <div className="space-y-2">
              <Label htmlFor="confirmPassword">Confirm Password</Label>
              <div className="relative">
                <Input
                  id="confirmPassword"
                  type={showConfirm ? "text" : "password"}
                  placeholder="Re-enter your password"
                  value={form.confirmPassword}
                  onChange={update("confirmPassword")}
                  aria-invalid={!!errors.confirmPassword}
                  className={`h-11 rounded-xl pr-10 ${errors.confirmPassword ? "border-destructive focus-visible:ring-destructive" : ""}`}
                />
                <button
                  type="button"
                  onClick={() => setShowConfirm((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  aria-label={showConfirm ? "Hide password" : "Show password"}
                >
                  {showConfirm ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              {errors.confirmPassword && <p className="text-xs text-destructive">{errors.confirmPassword}</p>}
            </div>

            <Button
              type="submit"
              disabled={isSubmitting}
              className="h-11 w-full rounded-full bg-gradient-bloom text-base font-semibold text-white shadow-soft hover:opacity-90 disabled:opacity-70"
            >
              {isSubmitting ? (
                <span className="flex items-center justify-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Creating account...
                </span>
              ) : (
                "Create Account"
              )}
            </Button>
          </form>

          <p className="mt-8 text-center text-sm text-muted-foreground">
            Already have an account?{" "}
            <Link to="/login" className="font-semibold text-primary hover:underline">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
