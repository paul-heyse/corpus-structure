package Corpus::Harness;
use strict;
use warnings;
use parent 'TAP::Harness';
use JSON::PP;
sub _initialize {
    my ($self, $args) = @_;
    # pg_prove already selects pgTAP. Repeating --source pgTAP in 3.37 consumes
    # its options twice, replacing the configured endpoint with an empty hash.
    die 'expected exactly the native pgTAP source'
        unless ref($args->{sources}) eq 'HASH'
            && keys(%{$args->{sources}}) == 1
            && ref($args->{sources}{pgTAP}) eq 'HASH'
            && keys(%{$args->{sources}{pgTAP}});
    die 'execution replacement/ignore-exit is forbidden'
        if $args->{exec} || $args->{ignore_exit};
    open my $input, '<', $ENV{CORPUS_PGTAP_MANIFEST} or die "open launch manifest: $!";
    my $manifest = do { local $/; JSON::PP::decode_json(<$input>) };
    close $input;
    my $selected = $manifest->{launch};
    my $config = $args->{sources}{pgTAP};
    for my $key (qw(psql host port dbname username)) {
        die "missing/changed native pgTAP source option: $key"
            unless ref($selected) eq 'HASH' && defined($selected->{$key})
                && length($selected->{$key}) && defined($config->{$key})
                && !ref($config->{$key}) && $config->{$key} eq $selected->{$key};
    }
    # Explicit rules prevent both environment and cwd rulesfile discovery.
    $args->{rules} = {seq => '*'};
    $args->{jobs} = 1;
    return $self->SUPER::_initialize($args);
}
1;
