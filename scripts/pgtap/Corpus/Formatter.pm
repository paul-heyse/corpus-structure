package Corpus::Formatter;
use strict;
use warnings;
use parent 'TAP::Formatter::Base';
use TAP::Formatter::Session;
use JSON::PP;
use Corpus::Report;
sub open_test {
    my ($self, $name, $parser) = @_;
    return Corpus::Formatter::Session->new({formatter => $self, name => $name, parser => $parser});
}
sub summary { }
package Corpus::Formatter::Session;
use parent 'TAP::Formatter::Session';
sub header { }
sub result {
    my ($self, $result) = @_;
    unless ($self->{raw_stream}) {
        open my $fh, '>', $ENV{CORPUS_PGTAP_RAW} or die "open raw TAP: $!";
        $fh->autoflush(1);
        $self->{raw_stream} = $fh;
        $self->{raw} = '';
    }
    my $line = $result->raw . "\n";
    print {$self->{raw_stream}} $line;
    $self->{raw} .= $line;
}
sub close_test {
    my ($self) = @_;
    return if $self->{closed}++;
    close $self->{raw_stream} if $self->{raw_stream};
    open my $input, '<', $ENV{CORPUS_PGTAP_MANIFEST} or die "open manifest: $!";
    local $/;
    my $manifest = JSON::PP::decode_json(<$input>);
    my $report = Corpus::Report::analyze($self->{raw} || '', $manifest,
        {exit => $self->parser->exit, wait => $self->parser->wait});
    open my $output, '>', $ENV{CORPUS_PGTAP_REPORT} or die "open report: $!";
    print $output JSON::PP->new->canonical->encode($report);
    close $output;
}
1;
