{pkgs}: {
  deps = [
    pkgs.python311Full
    pkgs.python311Packages.pip
    pkgs.nginx
    pkgs.python311Packages.supervisor
    pkgs.python311Packages.gunicorn
  ];
}
