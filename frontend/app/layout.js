import './globals.css';

export const metadata = {
  title: 'GROWW AI Product Intelligence',
  description: 'AI-native Product Intelligence Copilot for GROWW app reviews',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
