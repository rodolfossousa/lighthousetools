"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  Box,
  Card,
  CardContent,
  TextField,
  Button,
  Typography,
  Alert,
  InputAdornment,
  IconButton,
} from "@mui/material";
import {
  Visibility,
  VisibilityOff,
  Login as LoginIcon,
} from "@mui/icons-material";
import { useAuth } from "@/lib/AuthContext";
import LighthouseLogo, { ShapeDigitalBadge } from "@/components/LighthouseLogo";

export default function LoginPage() {
  const router = useRouter();
  const { user, loading, login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!loading && user) {
      router.replace("/");
    }
  }, [loading, user, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);

    const err = await login(username, password);
    setSubmitting(false);

    if (err) {
      setError(err);
    } else {
      router.push("/");
    }
  };

  if (loading) return null;
  if (user) return null;

  return (
    <Box
      sx={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        bgcolor: "background.default",
        background: "linear-gradient(135deg, #0F1117 0%, #1A1D27 50%, #0F1117 100%)",
      }}
    >
      <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 3 }}>
      <Card sx={{ width: 420, p: 1 }}>
        <CardContent sx={{ p: 4 }}>
          <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center", mb: 4 }}>
            <LighthouseLogo size="large" />
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1.5 }}>
              Faça login para continuar
            </Typography>
          </Box>

          {error && (
            <Alert severity="error" sx={{ mb: 3 }}>
              {error}
            </Alert>
          )}

          <form onSubmit={handleSubmit}>
            <TextField
              fullWidth
              label="Utilizador"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              sx={{ mb: 2.5 }}
              autoFocus
              autoComplete="username"
            />
            <TextField
              fullWidth
              label="Senha"
              type={showPassword ? "text" : "password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              sx={{ mb: 3 }}
              autoComplete="current-password"
              slotProps={{
                input: {
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton onClick={() => setShowPassword(!showPassword)} edge="end">
                        {showPassword ? <VisibilityOff /> : <Visibility />}
                      </IconButton>
                    </InputAdornment>
                  ),
                },
              }}
            />
            <Button
              type="submit"
              variant="contained"
              fullWidth
              size="large"
              disabled={submitting || !username || !password}
              startIcon={<LoginIcon />}
              sx={{ py: 1.5, fontSize: 16 }}
            >
              {submitting ? "Entrando..." : "Entrar"}
            </Button>
          </form>
        </CardContent>
      </Card>
      <ShapeDigitalBadge size="medium" />
      </Box>
    </Box>
  );
}
