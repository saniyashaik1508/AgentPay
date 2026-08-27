import '@fontsource/space-grotesk/500.css';
import '@fontsource/space-grotesk/600.css';
import '@fontsource/space-grotesk/700.css';
import '@fontsource/inter/400.css';
import '@fontsource/inter/500.css';
import '@fontsource/inter/600.css';
import '@fontsource/jetbrains-mono/400.css';
import '@fontsource/jetbrains-mono/500.css';
import './globals.css';

export const metadata = {
  title: 'AgentPay — Trust & Growth Infrastructure for Agentic Commerce',
  description:
    'A trust layer between AI shopping agents and payment rails: agent identity, spend passports, a deterministic policy engine, and a full audit trail.',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="font-body bg-ink-900 text-fog-bright min-h-screen antialiased">
        {children}
      </body>
    </html>
  );
}
