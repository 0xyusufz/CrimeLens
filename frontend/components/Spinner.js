export default function Spinner({ size = "md" }) {
  const sizeClasses = {
    sm: "w-4 h-4 border-2",
    md: "w-8 h-8 border-3",
    lg: "w-12 h-12 border-4"
  };
  
  // Minimal inline CSS for spinner since we don't have tailwind utilities
  return (
    <div className="spinner-container">
      <div className={`spinner ${sizeClasses[size]}`}></div>
      <style>{`
        .spinner-container {
          display: flex;
          justify-content: center;
          align-items: center;
          padding: 1rem;
        }
        .spinner {
          border: 3px solid rgba(255, 255, 255, 0.1);
          border-radius: 50%;
          border-top-color: var(--primary);
          animation: spin 1s ease-in-out infinite;
          width: 2rem;
          height: 2rem;
        }
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
