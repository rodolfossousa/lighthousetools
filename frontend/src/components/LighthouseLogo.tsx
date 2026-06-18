"use client";
import { Box, Typography } from "@mui/material";

interface LogoProps {
  size?: "small" | "medium" | "large";
  showText?: boolean;
  collapsed?: boolean;
}

function LighthouseIcon({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* Base */}
      <path d="M8 42 h32 l-4-4 H12 Z" fill="#3A7AE0" opacity="0.3"/>
      {/* Tower */}
      <path d="M18 38 L20 12 h8 L30 38 Z" fill="#5C9DFF"/>
      {/* Stripes */}
      <rect x="19.5" y="18" width="9" height="3" rx="0.5" fill="#FFFFFF" opacity="0.35"/>
      <rect x="19" y="24" width="10" height="3" rx="0.5" fill="#FFFFFF" opacity="0.35"/>
      <rect x="18.5" y="30" width="11" height="3" rx="0.5" fill="#FFFFFF" opacity="0.35"/>
      {/* Lamp house */}
      <rect x="19" y="8" width="10" height="5" rx="1.5" fill="#8BBBFF"/>
      {/* Beams */}
      <path d="M19 10.5 L6 6 L8 12 Z" fill="#FFA726" opacity="0.5"/>
      <path d="M29 10.5 L42 6 L40 12 Z" fill="#FFA726" opacity="0.5"/>
      {/* Glow */}
      <circle cx="24" cy="10.5" r="2.5" fill="#FFA726"/>
      <circle cx="24" cy="10.5" r="1.5" fill="#FFD54F"/>
      {/* Dome */}
      <path d="M21 8 Q24 3 27 8 Z" fill="#3A7AE0"/>
      {/* Door */}
      <rect x="22" y="33" width="4" height="5" rx="2" fill="#3A7AE0"/>
    </svg>
  );
}

export default function LighthouseLogo({ size = "medium", showText = true, collapsed = false }: LogoProps) {
  const iconSize = size === "large" ? 48 : size === "medium" ? 36 : 28;
  const titleSize = size === "large" ? "h5" : size === "medium" ? "subtitle1" : "body2";
  const subtitleSize = size === "large" ? 12 : 10;

  if (collapsed) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 0.5 }}>
        <LighthouseIcon size={28} />
      </Box>
    );
  }

  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
      <LighthouseIcon size={iconSize} />
      {showText && (
        <Box sx={{ minWidth: 0 }}>
          <Typography variant={titleSize as any} sx={{ fontWeight: 700, lineHeight: 1.2, color: "primary.main" }} noWrap>
            Lighthouse
          </Typography>
          <Typography variant="caption" sx={{ fontSize: subtitleSize, color: "text.secondary", fontWeight: 500, letterSpacing: 0.5 }} noWrap>
            Tools
          </Typography>
        </Box>
      )}
    </Box>
  );
}

export function ShapeDigitalBadge({ size = "small" }: { size?: "small" | "medium" }) {
  const h = size === "medium" ? 20 : 14;
  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, opacity: 0.6 }}>
      <svg width={h} height={h} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <polygon points="4,20 12,4 20,20" fill="#5C9DFF" opacity="0.8"/>
        <circle cx="15" cy="14" r="6" fill="#FF8A65" opacity="0.7"/>
      </svg>
      <Typography variant="caption" sx={{ fontSize: size === "medium" ? 11 : 9, color: "text.secondary", fontWeight: 500, letterSpacing: 0.3 }}>
        Shape Digital
      </Typography>
    </Box>
  );
}
