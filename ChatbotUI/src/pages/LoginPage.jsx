import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { login, register } from "../services/authService.js";
import { save as saveStorage, saveSession } from "../utils/storage.js";
import toast from "react-hot-toast";
import { INSTITUTION } from "../config/institution.js";

const LoginPage = ({ initialMode = "login" }) => {
	const [isLogin, setIsLogin] = useState(initialMode !== "signup");
	const [form, setForm] = useState({
		email: "",
		password: "",
		firstName: "",
		lastName: "",
		phoneNumber: "",
	});
	const [error, setError] = useState("");
	const navigate = useNavigate();
	const isValidEmail = (value) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
	const hasUppercase = (value) => /[A-Z]/.test(value);

	const handleChange = (event) => {
		const { name, value } = event.target;
		setForm((prev) => ({ ...prev, [name]: value }));
	};

	const handleSubmit = async (event) => {
		event.preventDefault();
		setError("");
		if (hasUppercase(form.email)) {
			setError("Please enter a valid email address.");
			return;
		}
		if (!isValidEmail(form.email)) {
			setError("Please enter a valid email address.");
			return;
		}
		if (!isLogin && form.password.length < 12) {
			setError("Create a password with at least 12 characters.");
			return;
		}
		try {
			if (isLogin) {
				const response = await login({
					email: form.email,
					password: form.password,
				});
				const { success, data, message } = response.data || {};
				if (success) {
					if (data?.bearer_token) {
						saveSession("AuthToken", data.bearer_token);
					}
					if (data) {
						saveStorage("UserProfile", data);
					}
					saveStorage("UserEmail", form.email);
					navigate("/NNMC");
				} else {
					setError(message || "Login failed. Please check your credentials.");
				}
				return;
			}

			const payload = {
				firstName: form.firstName,
				lastName: form.lastName,
				email: form.email,
				phoneNumber: form.phoneNumber,
				password: form.password,
			};
			const response = await register(payload);
			const { success, message } = response.data || {};
			if (success) {
				toast.success("Registration successful! You can now login.");
				setIsLogin(true);
			} else {
				setError(message || "Registration failed.");
			}
		} catch (err) {
			const serverMessage =
				err.response?.data?.message ||
				err.response?.data?.detail ||
				err.message;
			if (err.message === "Network Error") {
				setError(
					"Network Error: unable to reach the backend API. Check VITE_API_BASE_URL and CORS_ORIGINS on your deployed backend."
				);
				return;
			}
			setError(
				serverMessage || "Something went wrong. Please try again later."
			);
		}
	};

	return (
		<section className="min-h-screen w-full flex items-center justify-center bg-slate-100">
			<div className="max-w-md w-full bg-white border border-slate-200 rounded-xl shadow-lg p-8 space-y-6">
				<header className="space-y-2 text-center">
					<img
						src={INSTITUTION.logoUrl}
						alt="Northern New Mexico College"
						className="mx-auto h-16 w-auto"
					/>
					<h1 className="text-2xl font-semibold text-slate-900">
						{isLogin ? "Welcome Back" : "Create your Account"}
					</h1>
					<p className="text-sm text-slate-600">
						{isLogin
							? "Sign in to continue your NNMC academic plan."
							: "Register to build a Northern New Mexico College education plan."}
					</p>
				</header>

				{error && (
					<div className="bg-rose-50 text-rose-700 border border-rose-100 rounded-lg px-4 py-3 text-sm">
						{error}
					</div>
				)}

				<form onSubmit={handleSubmit} className="space-y-4">
					{!isLogin && (
						<div className="grid grid-cols-1 md:grid-cols-2 gap-3">
							<label className="text-sm text-slate-600 space-y-1">
								<span className="font-semibold">First Name</span>
								<input
									name="firstName"
									value={form.firstName}
									onChange={handleChange}
									className="w-full px-3 py-2 rounded-lg border border-slate-200"
									required
								/>
							</label>
							<label className="text-sm text-slate-600 space-y-1">
								<span className="font-semibold">Last Name</span>
								<input
									name="lastName"
									value={form.lastName}
									onChange={handleChange}
									className="w-full px-3 py-2 rounded-lg border border-slate-200"
									required
								/>
							</label>
						</div>
					)}

					<label className="text-sm text-slate-600 space-y-1">
						<span className="font-semibold">Email</span>
						<input
							type="email"
							name="email"
							value={form.email}
							onChange={handleChange}
							placeholder="student@nnmc.edu"
							autoCapitalize="none"
							autoCorrect="off"
							pattern="[a-z0-9._%+-]+@[a-z0-9.-]+\\.[a-z]{2,}$"
							title="Use a lowercase email address."
							className="w-full px-3 py-2 rounded-lg border border-slate-200"
							required
						/>
					</label>

					{!isLogin && (
						<label className="text-sm text-slate-600 space-y-1">
							<span className="font-semibold">Contact Number</span>
							<input
								name="phoneNumber"
							type="tel"
							autoComplete="tel"
							minLength={7}
							maxLength={32}
								value={form.phoneNumber}
								onChange={handleChange}
								className="w-full px-3 py-2 rounded-lg border border-slate-200"
								required
							/>
						</label>
					)}

					<label className="text-sm text-slate-600 space-y-1">
						<span className="font-semibold">Password</span>
						<input
							type="password"
							name="password"
							value={form.password}
							onChange={handleChange}
							placeholder="********"
							autoComplete={isLogin ? "current-password" : "new-password"}
							minLength={isLogin ? 1 : 12}
							maxLength={128}
							className="w-full px-3 py-2 rounded-lg border border-slate-200"
							required
						/>
						{!isLogin && (
							<span className="block text-xs text-slate-500">
								Use at least 12 characters.
							</span>
						)}
					</label>

					<button
						type="submit"
						className="w-full px-4 py-2.5 rounded-lg bg-slate-900 text-white font-medium hover:bg-slate-700"
					>
						{isLogin ? "Login" : "Sign Up"}
					</button>
				</form>

				<footer className="text-center text-sm text-slate-500">
					{isLogin ? (
						<>
							Don&apos;t have an account?{" "}
							<button
								type="button"
								onClick={() => setIsLogin(false)}
								className="text-indigo-600 hover:text-indigo-500 font-medium"
							>
								Create One
							</button>
						</>
					) : (
						<>
							Already have an account?{" "}
							<button
								type="button"
								onClick={() => setIsLogin(true)}
								className="text-indigo-600 hover:text-indigo-500 font-medium"
							>
								Sign In
							</button>
						</>
					)}
				</footer>
			</div>
		</section>
	);
};

export default LoginPage;
