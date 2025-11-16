import { Link, useLocation } from 'react-router-dom';

function Breadcrumbs() {
  const location = useLocation();
  const pathnames = location.pathname.split('/').filter(x => x);

  // Map route segments to readable names
  const routeNames = {
    deployments: 'Deployments',
    deploy: 'New Deployment',
    dashboard: 'Dashboard',
  };

  // Don't show breadcrumbs on home/dashboard
  if (pathnames.length === 0 || (pathnames.length === 1 && pathnames[0] === 'dashboard')) {
    return null;
  }

  return (
    <nav className="flex items-center space-x-2 text-sm text-gray-600 mb-6">
      {/* Home link */}
      <Link
        to="/"
        className="hover:text-blue-600 transition-colors"
      >
        Dashboard
      </Link>

      {pathnames.map((segment, index) => {
        const isLast = index === pathnames.length - 1;
        const path = `/${pathnames.slice(0, index + 1).join('/')}`;
        const name = routeNames[segment] || segment;

        return (
          <div key={path} className="flex items-center space-x-2">
            <span className="text-gray-400">/</span>
            {isLast ? (
              <span className="font-medium text-gray-900">{name}</span>
            ) : (
              <Link
                to={path}
                className="hover:text-blue-600 transition-colors"
              >
                {name}
              </Link>
            )}
          </div>
        );
      })}
    </nav>
  );
}

export default Breadcrumbs;
