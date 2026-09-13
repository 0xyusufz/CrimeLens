import "./globals.css";

export const metadata = {
  title: "CrimeLens",
  description: "Investigator-oriented crime analysis platform",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
