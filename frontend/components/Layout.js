"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { getToken } from "../lib/auth";
import Navbar from "./Navbar";
import Spinner from "./Spinner";

export default function AuthLayout({ children }) {
  const router = useRouter();
  const pathname = usePathname();
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = getToken();
    if (!token && pathname !== "/login") {
      router.replace("/login");
    } else if (token && pathname === "/login") {
      router.replace("/");
    } else {
      setIsAuthenticated(!!token);
      setLoading(false);
    }
  }, [pathname, router]);

  if (loading) {
    return (
      <div className="flex items-center justify-center" style={{ minHeight: "100vh" }}>
        <Spinner size="lg" />
      </div>
    );
  }

  if (!isAuthenticated && pathname !== "/login") {
    return null; // Will redirect
  }

  return (
    <div className="app-layout">
      {isAuthenticated && <Navbar />}
      <main className="main-content">
        {children}
      </main>
      <style>{`
        .app-layout {
          min-height: 100vh;
          display: flex;
          flex-direction: column;
        }
        .main-content {
          flex: 1;
          padding: 0;
        }
      `}</style>
    </div>
  );
}
