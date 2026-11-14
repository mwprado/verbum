# COPR SCM source method: make srpm
.PHONY: srpm
srpm:
	dnf -y install rpm-build git
	test -n "$(outdir)"
	set -eu; tmp=$$(mktemp -d); trap 'rm -rf "$$tmp"' EXIT; \
	  version=$$(rpmspec -q --srpm --qf '%{version}' package/verbum.spec); \
	  git archive --format=tar.gz --prefix="verbum-verbum-$$version/" HEAD > "$$tmp/verbum-$$version.tar.gz"; \
	  rpmbuild -bs package/verbum.spec --define "_sourcedir $$tmp" --define "_srcrpmdir $(outdir)" --nodeps
