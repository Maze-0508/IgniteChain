import { useNavigate } from 'react-router-dom';

export default function LoginButton() {
  const navigate = useNavigate();

  const handleLogin = () => {
    navigate('/login');
  };

  return (
    <div>
      <button
        className="text-lg font-semibold text-gray-900"
        onClick={handleLogin}
      >
        Login
      </button>
    </div>
  );
}
